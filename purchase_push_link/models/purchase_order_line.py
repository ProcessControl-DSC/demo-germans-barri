# Copyright 2025 Process Control
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import api, models


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    @api.depends("move_ids.state", "move_ids.quantity", "move_ids.product_uom_id")
    def _compute_qty_received(self):
        from_stock_lines = self.filtered(
            lambda line: line.qty_received_method == "stock_moves"
        )
        super(PurchaseOrderLine, self - from_stock_lines)._compute_qty_received()
        for line in from_stock_lines:
            qty_method = line.order_id.picking_type_id.qty_received_method
            total = 0.0
            for move in line._get_po_line_moves():
                if move.state == "done":
                    if move._is_purchase_return():
                        if not move.origin_returned_move_id or move.to_refund:
                            total -= move.product_uom_id._compute_quantity(
                                move.quantity,
                                line.product_uom_id,
                                rounding_method="HALF-UP",
                            )
                    elif (
                        move.origin_returned_move_id
                        and move.origin_returned_move_id._is_dropshipped()
                        and not move._is_dropshipped_returned()
                    ):
                        pass
                    elif (
                        move.origin_returned_move_id
                        and move.origin_returned_move_id._is_purchase_return()
                        and not move.to_refund
                    ):
                        pass
                    else:
                        if (
                            (not qty_method or qty_method == "second")
                            and move.location_dest_id.usage == "internal"
                            or qty_method == "first"
                            and move.location_dest_id.usage == "transit"
                            or qty_method == "dropshipping"
                            and move.location_dest_id.usage == "customer"
                        ):
                            total += move.product_uom_id._compute_quantity(
                                move.quantity,
                                line.product_uom_id,
                                rounding_method="HALF-UP",
                            )
            line._track_qty_received(total)
            line.qty_received = total
