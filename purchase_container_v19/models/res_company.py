# Copyright 2025 Process Control
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    is_active_container_planning_line = fields.Boolean(
        string="Gestión de líneas de contenedores",
        default=True,
        help="""Activa la gestión del 'Pendiente de recibir contenedores' en
        los albaranes de compra""",
    )
