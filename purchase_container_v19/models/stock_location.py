# Copyright 2025 Process Control
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import fields, models


class StockLocation(models.Model):
    _inherit = "stock.location"

    container_required = fields.Boolean(
        string="Contenedor requerido",
        default=True,
        help="En los albaranes cuya ubicación destino tenga marcada esta casilla, "
        "será necesario indicar el contenedor",
    )
