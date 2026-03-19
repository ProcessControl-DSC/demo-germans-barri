# Copyright 2025 Process Control
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import fields, models


class IntrastatCode(models.Model):
    _inherit = "account.intrastat.code"

    cost_percent = fields.Float(string="% de coste")
    has_cost_percent = fields.Boolean(
        string="¿Tiene % de coste?",
        help="Al marcar este campo, se puede establecer un % de coste. Si el % de "
        "coste va a ser 0, este campo no se debe marcar.",
    )

    def write(self, vals):
        if not vals.get("has_cost_percent", True):
            vals.update({"cost_percent": 0.0})
        return super().write(vals)
