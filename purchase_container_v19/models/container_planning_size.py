# Copyright 2025 Process Control
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import fields, models


class ContainerPlanningSize(models.Model):
    _name = "container.planning.size"
    _description = "Capacidad de contenedores"

    name = fields.Char("Nombre", required=True)

    _sql_constraints = [
        ("unique_name", "unique(name)", "Las capacidades deben ser únicas"),
    ]
