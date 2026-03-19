# -*- coding: utf-8 -*-
from odoo import api, fields, models


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    price_per_kg_move = fields.Float(
        string='Precio/kg',
        compute='_compute_price_per_kg_move',
        digits=(10, 4),
        help='Precio por kilogramo tomado del pedido de venta origen.',
    )

    @api.depends('move_id.sale_line_id.price_per_kg')
    def _compute_price_per_kg_move(self):
        for line in self:
            line.price_per_kg_move = line.move_id.sale_line_id.price_per_kg or 0.0
