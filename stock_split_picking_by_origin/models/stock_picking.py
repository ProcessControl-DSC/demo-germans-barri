# Copyright 2025 Process Control
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import models
from odoo.tools.float_utils import float_compare


class StockPicking(models.Model):
    _inherit = "stock.picking"

    def _action_done(self):
        res = super()._action_done()
        for picking in self:
            if picking.picking_type_id.split_picking_dest and picking.state == "done":
                backorder = self.env["stock.picking"].search(
                    [("backorder_id", "=", picking.id)]
                )
                # Solo dividir el destino si se generó una entrega parcial
                if backorder:
                    picking._split_picking_dest()
        return res

    def _split_picking_dest(self):
        self.ensure_one()
        picking_dests = self.env["stock.picking"]
        new_pickings = self.env["stock.picking"]
        for move in self.move_ids_without_package.move_dest_ids:
            if move.state not in ["cancel", "done"]:
                picking_dests |= move.picking_id
        for picking_dest in picking_dests:
            new_moves = self.env["stock.move"]
            for move_dest in picking_dest.move_ids_without_package:
                move_orig = self.env["stock.move"]
                for move in move_dest.move_orig_ids:
                    if move.state == "done" and move.picking_id == self:
                        move_orig |= move
                rounding = move_dest.product_uom.rounding
                # En v19, move.quantity (no quantity_done) refleja la cantidad procesada
                qty_done = sum(m.quantity for m in move_orig) or 0
                qty_initial = move_dest.product_uom_qty
                qty_diff_compare = float_compare(
                    qty_done, qty_initial, precision_rounding=rounding
                )
                if qty_done and qty_diff_compare < 0:
                    qty_split = qty_initial - qty_done
                    qty_uom_split = move_dest.product_uom._compute_quantity(
                        qty_split,
                        move_dest.product_id.uom_id,
                        rounding_method="HALF-UP",
                    )
                    new_move_vals = move_dest._split(qty_uom_split)
                    new_move = self.env["stock.move"].create(new_move_vals)
                    pend_move_origins = move_dest.move_orig_ids.filtered(
                        lambda m: m.state not in ["done", "cancel"]
                    )
                    done_move_origins = move_dest.move_orig_ids.filtered(
                        lambda m: m.state in ["done", "cancel"]
                    )
                    new_move.write(
                        {"move_orig_ids": [(3, move.id) for move in done_move_origins]}
                    )
                    move_dest.write(
                        {
                            "move_orig_ids": [
                                (3, move.id) for move in pend_move_origins
                            ],
                            "state": "assigned",
                        }
                    )
                    new_move._action_confirm(merge=False)
                    new_moves |= new_move
                elif not qty_done:
                    new_moves |= move_dest
            # Crear el picking de backorder con el método del OCA v19
            if new_moves:
                backorder_picking = picking_dest._create_split_order(
                    {"backorder_id": picking_dest.id}
                )
                new_pickings += backorder_picking
                new_moves.write({"picking_id": backorder_picking.id})
                new_moves.mapped("move_line_ids").write(
                    {"picking_id": backorder_picking.id}
                )
                new_moves._action_assign()
        return new_pickings
