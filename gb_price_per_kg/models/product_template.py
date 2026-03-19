# -*- coding: utf-8 -*-
from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    show_price_per_kg = fields.Boolean(
        string='Precio por KG',
        default=False,
        help='Activa la visualización del precio por kilogramo en las líneas '
             'de pedido de venta y en el albarán valorado.',
    )
