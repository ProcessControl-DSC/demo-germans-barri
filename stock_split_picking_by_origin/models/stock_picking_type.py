# Copyright 2025 Process Control
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import fields, models


class StockPickingType(models.Model):
    _inherit = "stock.picking.type"

    split_picking_dest = fields.Boolean(
        string="¿Dividir albarán de destino?",
        help="Al validar un albarán con este tipo de operación, si las líneas tienen "
        "un movimiento de destino relacionado, dicho movimiento se dividirá "
        "(si es necesario) para que quede exactamente igual que su origen.",
    )
