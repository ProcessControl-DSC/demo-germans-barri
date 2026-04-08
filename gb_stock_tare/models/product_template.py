# -*- coding: utf-8 -*-
from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    tare_per_unit = fields.Float(
        string='Tara por bulto (kg)',
        digits=(10, 3),
        help='Peso del embalaje por unidad/bulto (kg). '
             'Se usa para calcular automáticamente la tara total '
             'en recepciones y expediciones.',
    )
