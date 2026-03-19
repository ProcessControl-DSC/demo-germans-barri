# Copyright 2025 Process Control
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    split_method_landed_cost = fields.Selection(
        selection_add=[("by_intrastat", "Por código arancelario")],
        ondelete={"by_intrastat": "cascade"},
    )
