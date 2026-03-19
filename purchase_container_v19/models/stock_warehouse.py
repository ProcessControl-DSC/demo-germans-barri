# Copyright 2025 Process Control
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import fields, models


class StockWarehouse(models.Model):
    _inherit = "stock.warehouse"

    location_dest_container_id = fields.Many2one(
        comodel_name="stock.location",
        string="Ubicación de recepción de contenedores",
        domain=[("usage", "=", "internal")],
    )
