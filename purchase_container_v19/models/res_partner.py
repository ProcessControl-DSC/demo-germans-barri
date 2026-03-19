# Copyright 2025 Process Control
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    type = fields.Selection(
        selection_add=[
            ("shipping_company", "Shipping Company"),
            ("freight_forwarder", "Freight forwarder"),
        ]
    )
