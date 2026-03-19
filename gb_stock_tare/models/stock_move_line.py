# -*- coding: utf-8 -*-
from odoo import api, fields, models

_KG_FACTOR = 1000.0


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    gross_weight = fields.Float(
        string='Peso Bruto (kg)',
        digits=(10, 3),
        help='Peso bruto medido en báscula (envase + producto), en kg.',
    )
    tare_weight = fields.Float(
        string='Tara (kg)',
        digits=(10, 3),
        help='Peso del embalaje o envase (kg). Se resta al bruto para obtener el neto.',
    )
    net_weight = fields.Float(
        string='Peso Neto (kg)',
        compute='_compute_net_weight',
        store=True,
        digits=(10, 3),
        help='Peso neto = Peso bruto - Tara.',
    )

    @api.depends('gross_weight', 'tare_weight')
    def _compute_net_weight(self):
        for line in self:
            line.net_weight = max(0.0, (line.gross_weight or 0.0) - (line.tare_weight or 0.0))

    @api.onchange('gross_weight', 'tare_weight')
    def _onchange_weights_update_qty(self):
        """Propone qty_done = peso_neto / kg_por_uom cuando se usan UdM de peso."""
        for line in self:
            if not line.gross_weight and not line.tare_weight:
                continue
            uom = line.product_uom_id
            if uom and uom.factor and uom.factor >= _KG_FACTOR:
                kg_per_uom = uom.factor / _KG_FACTOR
                net = max(0.0, (line.gross_weight or 0.0) - (line.tare_weight or 0.0))
                if kg_per_uom:
                    line.qty_done = net / kg_per_uom
