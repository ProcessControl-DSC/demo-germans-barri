# Copyright 2025 Process Control
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from datetime import timedelta

from odoo import api, fields, models


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    def _default_date_new(self):
        for line in self:
            line.date_new = line.date_order or fields.Datetime.now()

    @api.depends(
        "move_ids",
        "move_ids.location_dest_id.usage",
        "move_ids.product_uom_qty",
        "move_ids.state",
        "price_unit",
        "product_qty",
    )
    def _compute_pending(self):
        if self.env.context.get("avoid_recompute_pending"):
            return
        values = {}
        for line in self:
            qty = line._get_qty_pending()
            percent_pending = (qty / line.product_qty) * 100 if line.product_qty else 0
            pending_amount = qty * line.price_unit
            values.setdefault(line.order_id, []).append(
                (
                    1,
                    line.id,
                    {
                        "qty_pending": qty,
                        "percent_pending": percent_pending,
                        "pending_amount": pending_amount,
                    },
                )
            )
        for purchase, line_values in values.items():
            purchase.update({"order_line": line_values})

    date_new = fields.Datetime(
        string="Nueva fecha", copy=False, default=_default_date_new
    )
    delay = fields.Integer(
        string="Retraso", readonly=True, compute="_compute_delay", store=True
    )
    date_claim = fields.Date(string="Fecha reclamación", copy=False)
    qty_pending = fields.Float(
        string="Cantidad pendiente", compute="_compute_pending", store=True
    )
    percent_pending = fields.Float(
        string="% pendiente", compute="_compute_pending", store=True
    )
    pending_amount = fields.Float(
        string="Importe pendiente",
        store=True,
        digits="Product Price",
        compute="_compute_pending",
    )
    state2 = fields.Many2one(
        comodel_name="purchase.order.line.state", string="Estado llegada", copy=False
    )
    notes = fields.Text(string="Observaciones", copy=False)
    date_order = fields.Datetime(copy=False)

    @api.depends("date_new", "date_planned")
    def _compute_delay(self):
        for line in self:
            if line.date_new and line.date_planned:
                line.delay = (line.date_new - line.date_planned).days

    def _update_relateds_moves_date(self, new_date):
        new_datetime = fields.Datetime.from_string(new_date)
        moves2update = self.env["stock.move"]
        for line in self:
            dummy_location_dest = (
                line.move_ids[0].location_dest_id if line.move_ids else False
            )
            if dummy_location_dest and all(
                move.location_dest_id.usage == dummy_location_dest.usage
                for move in line.move_ids
            ):
                for move in line.move_ids:
                    if move.state not in ["done", "cancel"] and not move.container_id:
                        moves2update |= move
            else:
                for move in line.move_ids:
                    if (
                        move.location_dest_id.usage == "transit"
                        and move.state not in ["done", "cancel"]
                        and not move.container_id
                    ):
                        move.write({"date": new_date, "date_deadline": new_date})
                        for move_dest in move.move_dest_ids:
                            if move_dest.state not in ["done", "cancel"]:
                                date = new_datetime + timedelta(
                                    days=move_dest.purchase_id.transit_days
                                )
                                move_dest.write({"date": date, "date_deadline": date})
        if moves2update:
            moves2update.write({"date": new_date, "date_deadline": new_date})
        return True

    def write(self, vals):
        res = super().write(vals)
        if vals.get("date_new", False):
            self._update_relateds_moves_date(vals["date_new"])
        if vals.get("product_qty", False):
            self._update_moves_date()
        return res

    def _prepare_stock_moves(self, picking):
        self.ensure_one()
        res = super()._prepare_stock_moves(picking)
        if picking and picking.location_dest_id.usage == "transit":
            for value in res:
                value.update(
                    {
                        "date_deadline": self.order_id.date_planned,
                        "date": self.order_id.date_planned,
                    }
                )
        elif picking and picking.location_dest_id.usage == "internal":
            for value in res:
                value.update(
                    {
                        "date_deadline": self.date_planned
                        or self.order_id.date_service,
                        "date": self.date_planned or self.order_id.date_service,
                    }
                )
        return res

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals["date_new"] = vals.get("date_planned")
        return super().create(vals_list)

    def _update_transit_moves_date(self):
        self.ensure_one()
        transit_date = self.date_planned or self.order_id.date_planned
        if not transit_date:
            return True
        moves = self.env["stock.move"]
        for move in self.move_ids:
            if move.location_dest_id.usage == "transit":
                moves |= move
        moves.write({"date": transit_date, "date_deadline": transit_date})
        return True

    def _update_internal_moves_date(self):
        self.ensure_one()
        internal_date = self.order_id.date_service
        if self.date_planned:
            internal_date = self.date_planned + timedelta(
                days=self.order_id.transit_days
            )
        if not internal_date:
            return True
        moves = self.env["stock.move"]
        for move in self.move_ids:
            if "production_id" in move.move_orig_ids._fields:
                if (
                    move.location_dest_id.usage == "internal"
                    and move.move_orig_ids
                    and not move.move_orig_ids.production_id
                ):
                    moves |= move
            else:
                if move.location_dest_id.usage == "internal" and move.move_orig_ids:
                    moves |= move
        moves.write({"date": internal_date, "date_deadline": internal_date})
        return True

    def _get_qty_pending(self):
        self.ensure_one()
        qty = 0.0
        if self.move_ids:
            order = self.order_id
            usage = order.picking_type_id.default_location_dest_id.usage or "internal"
            states = {"cancel", "draft", "done"}
            for move in self.move_ids:
                if move.state not in states and move.location_dest_id.usage == usage:
                    qty += move.product_uom_qty
        return qty

    @api.model
    def _get_date_planned(self, seller, po=False):
        if self.env.context.get("bypass_set_line_date_from_order"):
            return super()._get_date_planned(seller, po)
        date_planned = self.order_id.date_planned
        if not date_planned and po:
            date_planned = po.date_planned
        if not date_planned:
            date_planned = super()._get_date_planned(seller, po)
        return date_planned

    def _update_moves_date(self):
        self.ensure_one()
        internal_date = self.date_new
        if self.order_id.transit_days and self.date_new:
            internal_date = self.date_new + timedelta(days=self.order_id.transit_days)
        transit_date = self.date_new
        internal_moves = self.env["stock.move"]
        transit_moves = self.env["stock.move"]
        for move in self.move_ids:
            if move.state not in ["done", "cancel"]:
                if move.location_dest_id.usage == "internal":
                    internal_moves |= move
                if move.location_dest_id.usage == "transit":
                    transit_moves |= move
        if internal_moves:
            internal_moves.write(
                {"date": internal_date, "date_deadline": internal_date}
            )
        if transit_moves:
            transit_moves.write({"date": transit_date, "date_deadline": internal_date})
        return True
