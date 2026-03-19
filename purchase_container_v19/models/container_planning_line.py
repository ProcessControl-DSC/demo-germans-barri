# Copyright 2025 Process Control
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import fields, models


class ContainerPlanningLine(models.Model):
    _name = "container.planning.line"
    _description = "Líneas de contenedores"

    def _compute_move_dest_ids(self):
        for line in self:
            line.move_dest_ids = line.move_transit_id.move_dest_ids

    name = fields.Char(related="container_id.name", string="Nombre")
    container_id = fields.Many2one(
        "container.planning", string="Contenedor", readonly=True
    )
    state = fields.Selection(related="container_id.state", string="Estado", store=True)
    arrival_date = fields.Date(
        related="container_id.arrival_date", string="Fecha de llegada"
    )
    product_id = fields.Many2one("product.product", string="Producto", readonly=True)
    purchase_id = fields.Many2one(
        "purchase.order", string="Pedido de compra", readonly=True
    )
    product_uom_qty = fields.Float(
        "Cant. inicial",
    )
    qty_done_transit = fields.Float(
        "Cant. transito",
    )
    qty_done_stock = fields.Float(
        "Cant. recibida",
    )
    pending_qty = fields.Float(
        "Cant. pendiente",
    )
    move_dest_ids = fields.One2many(
        "stock.move",
        "container_line_id",
        compute="_compute_move_dest_ids",
        string="Movimientos destino",
    )
    picking_id = fields.Many2one("stock.picking", string="Albarán", readonly=True)
    move_transit_id = fields.Many2one(
        "stock.move",
        string="Movimiento transito",
    )

    def action_view_moves_dest(self):
        self.ensure_one()
        return {
            "name": "Movimientos destino",
            "type": "ir.actions.act_window",
            "res_model": "container.planning.line",
            "view_mode": "form",
            "view_id": self.env.ref(
                "purchase_container.container_planning_line_view_form"
            ).id,
            "target": "new",
            "res_id": self.id,
        }
