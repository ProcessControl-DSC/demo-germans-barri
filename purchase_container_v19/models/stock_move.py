# Copyright 2025 Process Control
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from datetime import timedelta

from odoo import api, fields, models


class StockMove(models.Model):
    _inherit = "stock.move"

    @api.depends("picking_id", "picking_id.force_container_id")
    def _compute_force_container(self):
        for move in self:
            move.update({"force_container_id": move.picking_id.force_container_id.id})

    def _inverse_force_container(self):
        return True

    force_container_id = fields.Many2one(
        comodel_name="container.planning",
        string="Contenedor forzado",
        compute="_compute_force_container",
        inverse="_inverse_force_container",
        store=True,
        help="Contenedor establecido manualmente por el usuario",
    )
    container_id = fields.Many2one(
        comodel_name="container.planning",
        string="Contenedor",
        related="picking_id.container_id",
        store=True,
    )
    purchase_id = fields.Many2one(
        comodel_name="purchase.order",
        string="Pedido compra",
        related="purchase_line_id.order_id",
    )
    # Campo de fecha esperada original (independiente de la fecha programada actual)
    date_expected = fields.Datetime(
        "Expected Date",
        default=fields.Datetime.now,
        index=True,
        required=True,
        help="Scheduled date for the processing of this move",
    )
    company_currency_id = fields.Many2one(
        comodel_name="res.currency",
        store=True,
        related="container_id.company_currency_id",
        string="Moneda compañía",
    )
    usd_currency_id = fields.Many2one(
        comodel_name="res.currency",
        string="Moneda $",
        related="container_id.usd_currency_id",
        store=True,
    )
    cost_usd = fields.Monetary(
        string="Precio compra ($)", currency_field="usd_currency_id"
    )
    cost_eur = fields.Monetary(
        string="Precio compra (€)", currency_field="company_currency_id"
    )
    transport_cost = fields.Monetary(
        string="Coste transporte (€)", currency_field="company_currency_id"
    )
    customs_fees = fields.Monetary(
        string="Aranceles", currency_field="company_currency_id"
    )
    total_cost = fields.Monetary(
        string="Coste total", currency_field="company_currency_id"
    )
    unit_cost = fields.Monetary(
        string="Coste unitario", currency_field="company_currency_id"
    )
    origin_port = fields.Char(string="Puerto origen", related="purchase_id.origin_port")
    container_line_id = fields.Many2one(
        comodel_name="container.planning.line",
        string="Línea de contenedor",
    )

    def _update_container_cost_values(self, volume, transport_cost):
        for move in self:
            move.write(move._get_container_cost_values(volume, transport_cost))
        return True

    def _get_container_cost_values(self, total_volume, transport_cost):
        container = self.picking_id.container_id
        cost_usd = self._get_po_price_subtotal(self.purchase_line_id)
        transport_cost = (
            (self.volume * transport_cost) / total_volume if total_volume else 0
        )
        # En v19 el campo hs_code_id fue renombrado a intrastat_code_id.
        # El campo cost_percent lo aporta el módulo intrastat_landed_cost_oca.
        intrastat_code = self.product_id.intrastat_code_id
        customs_fees = ((cost_usd * container.currency_rate) + transport_cost) * (
            intrastat_code.cost_percent if intrastat_code else 1 / 100
        )
        if container.bank_expenses:
            customs_fees += customs_fees * (container.bank_expenses / 100)
        cost_eur = cost_usd / (container.currency_rate or 1.0)
        total_cost = cost_eur + transport_cost + customs_fees
        unit_cost = total_cost / (self.product_uom_qty or 1.0)
        return {
            "cost_usd": cost_usd,
            "cost_eur": cost_eur,
            "transport_cost": transport_cost,
            "customs_fees": customs_fees,
            "total_cost": total_cost,
            "unit_cost": unit_cost,
        }

    def _get_po_price_subtotal(self, po_line):
        price_unit = po_line.price_unit
        if po_line._fields.get("discount"):
            price_unit = po_line.price_unit * (1 - po_line.discount / 100)
        return price_unit * self.product_uom_qty

    def _set_move_dest_date_expected_from_transit(self):
        for move in self:
            domain = [
                ("move_orig_ids", "in", move.ids),
                ("state", "not in", ["done", "cancel"]),
            ]
            move_dest = self.env["stock.move"].search(domain)
            if move_dest:
                transit_days = move.purchase_line_id.order_id.transit_days
                date = move.date_expected + timedelta(days=transit_days)
                move_dest.write({"date_expected": date, "date": date})
        return True

    def _merge_moves_fields(self):
        res = super()._merge_moves_fields()
        if self.picking_id.picking_type_id.merge_moves_keep_date:
            res["date"] = self.sorted("create_date")[0].date
        return res
