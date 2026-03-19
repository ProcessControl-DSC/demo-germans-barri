# -*- coding: utf-8 -*-
from odoo import api, fields, models

# Factor del kg en gramos (unidad raíz de la cadena de pesos en Odoo 19)
_KG_FACTOR = 1000.0


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    price_per_kg = fields.Float(
        string='Precio/kg',
        compute='_compute_price_per_kg',
        store=True,
        digits=(10, 4),
        help='Precio unitario expresado en EUR/kg. '
             'Calculado automáticamente a partir del precio y la unidad de medida.',
    )

    @api.depends('price_unit', 'product_uom_id', 'product_id.show_price_per_kg')
    def _compute_price_per_kg(self):
        for line in self:
            uom = line.product_uom_id
            if (
                uom
                and line.product_id.show_price_per_kg
                and uom.factor
                and uom.factor >= _KG_FACTOR
            ):
                # factor está en gramos; dividimos por 1000 para obtener kg
                kg_count = uom.factor / _KG_FACTOR
                line.price_per_kg = line.price_unit / kg_count if kg_count else 0.0
            else:
                line.price_per_kg = 0.0
