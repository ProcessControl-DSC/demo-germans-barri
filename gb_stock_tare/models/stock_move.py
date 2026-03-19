# -*- coding: utf-8 -*-
from odoo import api, fields, models


class StockMove(models.Model):
    _inherit = 'stock.move'

    gross_weight_total = fields.Float(
        string='Peso Bruto Total (kg)',
        compute='_compute_weight_totals',
        store=True,
        digits=(10, 3),
    )
    tare_weight_total = fields.Float(
        string='Tara Total (kg)',
        compute='_compute_weight_totals',
        store=True,
        digits=(10, 3),
    )
    net_weight_total = fields.Float(
        string='Peso Neto Total (kg)',
        compute='_compute_weight_totals',
        store=True,
        digits=(10, 3),
    )

    @api.depends(
        'move_line_ids.gross_weight',
        'move_line_ids.tare_weight',
        'move_line_ids.net_weight',
    )
    def _compute_weight_totals(self):
        for move in self:
            lines = move.move_line_ids
            move.gross_weight_total = sum(lines.mapped('gross_weight'))
            move.tare_weight_total = sum(lines.mapped('tare_weight'))
            move.net_weight_total = sum(lines.mapped('net_weight'))
