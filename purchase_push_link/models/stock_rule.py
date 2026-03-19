# Copyright 2025 Process Control
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import models


class StockRule(models.Model):
    _inherit = "stock.rule"

    def _push_prepare_move_copy_values(self, move_to_copy, new_date):
        vals = super()._push_prepare_move_copy_values(move_to_copy, new_date)
        if move_to_copy.purchase_line_id:
            vals.update(
                {
                    "partner_id": move_to_copy.purchase_line_id.order_id.partner_id.id,
                    "purchase_line_id": move_to_copy.purchase_line_id.id,
                    "price_unit": move_to_copy.price_unit,
                }
            )
        return vals
