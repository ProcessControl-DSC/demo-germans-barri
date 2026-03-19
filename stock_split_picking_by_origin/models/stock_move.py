# Copyright 2025 Process Control
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import models


class StockMove(models.Model):
    _inherit = "stock.move"

    def _search_picking_for_assignation_domain(self):
        domain = super()._search_picking_for_assignation_domain()
        if self.move_orig_ids and any(
            p.split_picking_dest for p in self.move_orig_ids.picking_type_id
        ):
            domain += [
                (
                    "id",
                    "in",
                    self.move_orig_ids.picking_id.move_ids.move_dest_ids.picking_id.ids,
                )
            ]
        return domain
