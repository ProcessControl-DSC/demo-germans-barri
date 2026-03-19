# Copyright 2025 Process Control
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import fields, models


class StockLocation(models.Model):
    _inherit = "stock.location"

    exclude_stock = fields.Boolean(
        string="¿Excluir stock?",
        help="Marca la casilla si no quieres que el stock de esta ubicación se "
        "tenga en cuenta para el cálculo de stock de las variantes de producto",
        copy=False,
    )

    def write(self, vals):
        res = super().write(vals)
        if "exclude_stock" in vals:
            if self.child_ids:
                self.child_ids.write({"exclude_stock": vals["exclude_stock"]})
        return res
