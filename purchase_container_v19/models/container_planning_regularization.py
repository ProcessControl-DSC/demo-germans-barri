# Copyright 2025 Process Control
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import _, api, exceptions, fields, models


class ContainerPlanningRegularization(models.Model):
    _name = "container.planning.regularization"
    _description = "Container planning regularization"

    product_id = fields.Many2one(
        comodel_name="product.product",
        string="Producto",
        required=True,
        readonly=True,
    )
    product_uom_qty = fields.Float(
        string="Cantidad",
        required=False,
        readonly=True,
    )
    note = fields.Text(
        string="Observaciones",
        readonly=True,
    )
    purchase_id = fields.Many2one(
        comodel_name="purchase.order",
        string="Pedido de compra",
        required=True,
        readonly=True,
        domain="[('order_line.product_id', '=', product_id)]",
    )
    purchase_line_id = fields.Many2one(
        comodel_name="purchase.order.line",
        string="Linea pedido de compra",
        required=True,
        readonly=True,
    )
    container_id = fields.Many2one(
        comodel_name="container.planning",
        string="Contenedor",
        readonly=True,
    )
    move_id = fields.Many2one(
        comodel_name="stock.move",
        string="Movimiento",
        readonly=True,
    )
    state = fields.Selection(
        selection=[("draft", "Borrador"), ("done", "Realizado")],
        string="Estado",
        default="draft",
    )
    tracking = fields.Selection(related="product_id.tracking", readonly=True)
    lot_id = fields.Many2one(
        comodel_name="stock.lot",
        string="Lote",
        readonly=True,
    )

    @api.onchange("purchase_id", "product_id")
    def onchange_purchase_product(self):
        if self.purchase_id and self.product_id:
            not_found = True
            for line in self.purchase_id.order_line:
                if line.product_id == self.product_id:
                    self.purchase_line_id = line.id
                    not_found = False
                    break
            if not_found:
                message = (
                    "El producto {} no se encuentra en el pedido de compra {}".format(
                        self.product_id.display_name, self.purchase_id.name
                    )
                )
                return {
                    "warning": {
                        "title": "Producto no encontrado",
                        "message": message,
                        "type": "notification",
                    },
                }

    @api.onchange("product_id")
    def onchange_purchase_product_autoasigned(self):
        purchase = self.env["purchase.order"].search(
            [("order_line.product_id", "=", self.product_id.id)]
        )
        if len(purchase) == 1:
            self.purchase_id = purchase.id

    def _create_regularization_move(self):
        supplier = self.purchase_id.partner_id
        qty = abs(self.product_uom_qty)
        location = supplier.property_stock_supplier
        if not location:
            raise exceptions.UserError(
                _("No hay ubicación del proveedor, revise el proveedor.")
            )
        warehouse = self.purchase_id.picking_type_id.warehouse_id
        if not warehouse:
            raise exceptions.UserError(
                _(
                    "No se ha encontrado un almacén relacionado con la operación {}"
                ).format(self.purchase_id.picking_type_id.display_name)
            )
        location_dest = warehouse.location_dest_container_id
        if not location_dest:
            raise exceptions.UserError(
                _(
                    "El almacén {} no tiene establecida una "
                    "ubicación de recepcion de contenedores."
                ).format(warehouse.display_name)
            )
        regularization_type = "incoming"
        if self.product_uom_qty < 0:
            regularization_type = "outgoing"
            location_aux = location
            location = location_dest
            location_dest = location_aux
        pickings = self.env["stock.picking"]
        for picking in self.container_id.regularization_picking_ids:
            if (
                picking.partner_id == supplier
                and picking.picking_type_id.code == regularization_type
            ):
                pickings |= picking
                break
        if pickings:
            picking = pickings[0]
        else:
            picking_type = self.env["stock.picking.type"].search(
                [
                    ("code", "=", regularization_type),
                    ("default_location_src_id", "=", location.id),
                    ("default_location_dest_id", "=", location_dest.id),
                ]
            )
            if not picking_type:
                raise exceptions.UserError(
                    _(
                        "No puede generarse el albarán de regularización, "
                        "ya que no se ha podido determinar el tipo de "
                        "albarán.\n- Tipo de operación '{}'\n- Ubicación de "
                        "origen: '{}'\n- Ubicación de destino: '{}'"
                    ).format(regularization_type, location.name, location_dest.name)
                )
            picking = self.env["stock.picking"].create(
                self._prepare_picking_vals(
                    supplier, location, location_dest, picking_type
                )
            )
        new_move = self.env["stock.move"].create(self._prepare_move_vals(qty, picking))
        self.env["stock.move.line"].create(self._prepare_move_line_vals(qty, new_move))
        new_move._action_done()
        self.write({"move_id": new_move.id, "state": "done"})
        return True

    def _prepare_picking_vals(
        self, supplier, location, location_dest, picking_type, date_order=None
    ):
        vals = {
            "partner_id": supplier.id,
            "location_id": location.id,
            "location_dest_id": location_dest.id,
            "picking_type_id": picking_type.id,
            "purchase_id": self.purchase_id.id,
        }
        if date_order:
            vals.update({"date": date_order})
        return vals

    def _prepare_move_vals(self, qty, picking):
        vals = {
            "product_id": self.product_id.id,
            "name": self.product_id.display_name,
            "product_uom_qty": qty,
            "product_uom": self.product_id.uom_id.id,
            "location_id": picking.location_id.id,
            "location_dest_id": picking.location_dest_id.id,
            "purchase_line_id": self.purchase_line_id.id,
            "picking_id": picking.id,
        }
        if (
            picking.picking_type_id.code == "outgoing"
            and picking.picking_type_id.to_refund
        ):
            vals.update({"to_refund": True})
        return vals

    def _prepare_move_line_vals(self, qty, move):
        return {
            "picking_id": move.picking_id.id,
            "move_id": move.id,
            "product_id": move.product_id.id,
            "location_id": move.location_id.id,
            "location_dest_id": move.location_dest_id.id,
            "lot_id": self.lot_id.id
            if self.lot_id and self.tracking != "none"
            else False,
            "quantity": qty,
            "product_uom_id": move.product_uom.id,
        }

    def _regularize_qty(self):
        for move in self.purchase_line_id.move_ids:
            if (
                move.state not in ["cancel", "done"]
                and move.picking_id.picking_type_id.code == "incoming"
            ):
                if move.product_uom_qty - self.product_uom_qty > 0:
                    new_qty = move.product_uom_qty - self.product_uom_qty
                    move.write({"product_uom_qty": new_qty})
                    return True
        return False

    def _create_supplier2transit_picking(self):
        order = self.purchase_id
        pickings = self.env["stock.picking"]
        for picking in order.picking_ids:
            if (
                picking.state not in ["cancel", "done"]
                and picking.picking_type_id.id == order.picking_type_id.id
            ):
                pickings |= picking
        if pickings:
            picking = pickings[0]
        else:
            location = order.partner_id.property_stock_supplier
            warehouse_id = order.picking_type_id.warehouse_id
            location_dest = warehouse_id and warehouse_id.location_dest_container_id
            picking = self.env["stock.picking"].create(
                self._prepare_picking_vals(
                    order.partner_id,
                    location,
                    location_dest,
                    order.picking_type_id,
                    date_order=order.date_planned,
                )
            )
        for vals in self.purchase_line_id._prepare_stock_moves(picking):
            qty = abs(self.product_uom_qty)
            vals["product_uom_qty"] = qty
            move = self.env["stock.move"].create(vals)
            move._action_confirm()
            self.env["stock.move.line"].create(self._prepare_move_line_vals(qty, move))
            for move_dest in move.move_dest_ids:
                if move_dest.state not in ["done", "cancel"]:
                    move_dest.date = order.date_service
                    move_dest.date_deadline = order.date_service
        return picking

    def action_done(self):
        """
        Buscamos un movimiento del mismo pedido y del mismo producto
        que no este ni cancelado ni realizado
        - Si product_uom_qty > 0 y hay un movimiento, le restamos la cantidad
        - Si product_uom_qty < 0 y hay un movimiento, le sumamos la cantidad
        - Si product_uom_qty < 0 y no hay un movimiento, creamos un albaran de
         proveedores a tránsito
        """
        for regularization in self:
            if regularization.state == "draft":
                regularization._create_regularization_move()
                regularize = regularization._regularize_qty()
                if not regularize and regularization.product_uom_qty < 0:
                    regularization._create_supplier2transit_picking()
        return True

    def unlink(self):
        if any(regularitzation.state == "done" for regularitzation in self):
            raise exceptions.UserError(
                _("No puede eliminar regularizaciones ya realizadas.")
            )
        return super().unlink()
