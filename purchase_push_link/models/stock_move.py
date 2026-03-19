# Copyright 2025 Process Control
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import models


class StockMove(models.Model):
    _inherit = "stock.move"

    def copy(self, default=None):
        self.ensure_one()
        if default is None:
            default = {}
        purchase_line_id = default.get("purchase_line_id", False)
        moves = super().copy(default=default)
        if purchase_line_id:
            moves.write({"purchase_line_id": purchase_line_id})
        return moves

    def _is_purchase_return(self):
        """Por defecto Odoo considera una devolución un albarán que va de una
        ubicación de tránsito a una ubicación interna. En recepciones en dos pasos
        este movimiento es parte del flujo normal, no una devolución."""
        return super()._is_purchase_return() and not (
            self.location_id.usage == "transit"
            and self.location_dest_id.usage == "internal"
        )

    def write(self, vals):
        res = super().write(vals)
        if "sequence" not in vals:
            return res
        for move in self:
            if not move.move_dest_ids or not move.purchase_line_id:
                continue
            for move_dest in move.move_dest_ids:
                move_dest.sequence = move.sequence + 1
        return res
