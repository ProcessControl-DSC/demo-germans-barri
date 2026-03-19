# Copyright 2025 Process Control
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import api, fields, models


class StockPickingType(models.Model):
    _inherit = "stock.picking.type"

    @api.depends("default_location_dest_id", "default_location_dest_id.usage")
    def _compute_qty_received_method(self):
        for picking_type in self:
            if picking_type.default_location_dest_id.usage != "transit":
                picking_type.qty_received_method = "second"

    def _inverse_qty_received_method(self):
        return

    qty_received_method = fields.Selection(
        string="Contabilizar cantidades desde",
        selection=[
            ("first", "Primer albarán"),
            ("second", "Segundo albarán"),
            ("dropshipping", "Albarán cliente (dropshipping)"),
        ],
        help="En configuraciones donde tenemos recepciones de mercancía en dos pasos o "
        "similares, podemos decidir desde qué albarán queremos contabilizar las "
        "cantidades recibidas de las líneas del pedido de compra",
        default="second",
        compute="_compute_qty_received_method",
        inverse="_inverse_qty_received_method",
        store=True,
    )
    default_dest_location_usage = fields.Selection(
        related="default_location_dest_id.usage"
    )
