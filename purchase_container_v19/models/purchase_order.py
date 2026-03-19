# Copyright 2025 Process Control
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from datetime import timedelta

from odoo import api, fields, models


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    # Override date_planned to make it a regular stored field (not computed).
    # In v19, the native date_planned is computed from order lines.
    # This client manages container logistics dates manually.
    date_planned = fields.Datetime(
        compute=False,
        required=True,
        default=fields.Datetime.now,
    )
    date_service = fields.Datetime(string="Fecha llegada")
    transit_days = fields.Integer(
        "Días en tránsito",
        copy=False,
        tracking=True,
        default=30,
        help="Al modificar este valor, se actualizará la fecha del albarán de tránsito "
        "a existencias, estableciendo la fecha del albarán de proveedor + nº días "
        "asignados aquí",
    )
    picking_type_dest_usage = fields.Selection(
        string="Location dest type",
        related="picking_type_id.default_location_dest_id.usage",
    )
    origin_port = fields.Char(string="Puerto origen")

    def button_confirm(self):
        res = super().button_confirm()
        self._update_move_dest_date_expected_from_transit()
        self._update_purchase_date_new_line()
        for order in self:
            for line in order.order_line:
                line._update_transit_moves_date()
                line._update_internal_moves_date()
        return res

    def _update_move_dest_date_expected_from_transit(self):
        for order in self:
            if order.picking_type_dest_usage != "transit":
                continue
            if order.transit_days:
                moves = self.env["stock.move"].search(
                    [
                        ("state", "not in", ["cancel", "done"]),
                        ("location_dest_id.usage", "=", "transit"),
                        ("picking_id.purchase_id", "=", order.id),
                    ]
                )
                moves.write({"date_expected": order.date_planned})
                moves._set_move_dest_date_expected_from_transit()
        return True

    def _update_purchase_date_new_line(self):
        for order in self:
            values = []
            for line in order.order_line:
                values += [(1, line.id, {"date_new": line.date_planned})]
            order.write({"order_line": values})
        return True

    @api.onchange("date_planned", "transit_days", "picking_type_id")
    def _onchange_dates(self):
        date_planned = self.date_planned
        vals = {"date_service": date_planned}
        if self.picking_type_dest_usage == "transit":
            if date_planned:
                vals["date_service"] = date_planned + timedelta(days=self.transit_days)
        self.update(vals)

    @api.onchange("date_planned")
    def _onchange_line_dates(self):
        vals = {}
        for line in self.order_line:
            if line.display_type:
                continue
            vals.setdefault("order_line", []).append(
                (1, line.id, {"date_planned": self.date_planned})
            )
        self.update(vals)

    def write(self, vals):
        res = super().write(vals)
        if "transit_days" in vals:
            self._update_transit_days_postprocess()
        return res

    def _update_transit_days_postprocess(self):
        for order in self:
            if order.picking_type_dest_usage != "transit":
                continue
            moves = self.env["stock.move"]
            for picking in order.picking_ids:
                for move in picking.move_ids_without_package:
                    usage = move.location_dest_id.usage
                    if usage == "transit" and move.state not in ["cancel", "done"]:
                        moves |= move
            moves._set_move_dest_date_expected_from_transit()
        return True
