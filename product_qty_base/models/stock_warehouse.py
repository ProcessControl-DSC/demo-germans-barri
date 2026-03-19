# Copyright 2025 Process Control
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import fields, models


class StockWarehouse(models.Model):
    _inherit = "stock.warehouse"

    consider_stock = fields.Boolean(
        string="¿Tener en cuenta stock?",
        help="Marca la casilla si quieres que el stock de este almacén se tenga en "
        "cuenta para el cálculo de stock de las variantes de producto",
        default=True,
    )
