# Copyright 2025 Process Control
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import fields, models


class PurchaseOrderLineState(models.Model):
    _name = "purchase.order.line.state"
    _description = "Estado de líneas pendientes de recibir"

    name = fields.Char(string="Nombre", required=True)
