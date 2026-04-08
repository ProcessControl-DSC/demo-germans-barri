# -*- coding: utf-8 -*-
from odoo import api, fields, models


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    gross_weight = fields.Float(
        string='Peso Bruto (kg)',
        digits=(10, 3),
        help='Peso total medido en báscula (producto + embalaje).',
    )
    package_qty = fields.Float(
        string='Nº Bultos',
        digits=(10, 0),
        help='Número de bultos/cajas/sacos pesados.',
    )
    tare_per_unit = fields.Float(
        string='Tara/bulto (kg)',
        related='product_id.tare_per_unit',
        readonly=True,
    )
    tare_weight = fields.Float(
        string='Tara Total (kg)',
        compute='_compute_tare_weight',
        store=True,
        digits=(10, 3),
        help='Tara total = Tara por bulto × Nº bultos.',
    )
    net_weight = fields.Float(
        string='Peso Neto (kg)',
        compute='_compute_net_weight',
        store=True,
        digits=(10, 3),
        help='Peso neto = Peso bruto − Tara total.',
    )

    @api.depends('package_qty', 'product_id.tare_per_unit')
    def _compute_tare_weight(self):
        for line in self:
            tare_unit = line.product_id.tare_per_unit or 0.0
            line.tare_weight = tare_unit * (line.package_qty or 0.0)

    @api.depends('gross_weight', 'tare_weight')
    def _compute_net_weight(self):
        for line in self:
            line.net_weight = max(
                0.0, (line.gross_weight or 0.0) - (line.tare_weight or 0.0)
            )

    @api.onchange('gross_weight', 'package_qty')
    def _onchange_weights_update_qty(self):
        """Actualiza qty_done con el peso neto convertido a la UdM de la línea."""
        for line in self:
            if not line.gross_weight:
                continue
            tare_unit = line.product_id.tare_per_unit or 0.0
            tare_total = tare_unit * (line.package_qty or 0.0)
            net = max(0.0, line.gross_weight - tare_total)
            uom = line.product_uom_id
            if uom and uom.factor and uom.factor >= 1000.0:
                kg_per_uom = uom.factor / 1000.0
                if kg_per_uom:
                    line.qty_done = net / kg_per_uom
            else:
                line.qty_done = net
