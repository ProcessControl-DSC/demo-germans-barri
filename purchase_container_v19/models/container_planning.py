# Copyright 2025 Process Control
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import _, api, exceptions, fields, models
from odoo.exceptions import ValidationError


class ContainerPlanning(models.Model):
    _name = "container.planning"
    _description = "Container planning"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date asc, departure_date asc, arrival_date asc"

    @api.depends("moves2transit_ids")
    def _compute_product_quantity(self):
        for container in self:
            container.product_quantity = sum(
                move.product_uom_qty for move in container.moves2transit_ids
            )

    def _compute_moves(self):
        for container in self:
            moves = container._get_moves()
            moves2transit = moves["transit"]
            moves2stock = moves["stock"]
            moves2stock_forced = self._get_forced_moves()
            if moves2stock_forced:
                moves2stock |= moves2stock_forced
            container.update(
                {
                    "moves2transit_ids": moves2transit,
                    "moves2stock_ids": moves2stock,
                }
            )

    def _compute_pickings(self):
        for container in self:
            pickings = container.regularization_ids.move_id.picking_id
            container.regularization_picking_ids = pickings

    @api.depends("moves2stock_ids")
    def _compute_picking_type(self):
        for container in self:
            picking_type = self.env["stock.picking.type"]
            for picking in container.moves2stock_ids.picking_id:
                if picking.picking_type_id:
                    picking_type = picking.picking_type_id
                    break
            container.update({"picking_type_id": picking_type.id})

    def _inverse_picking_type(self):
        for container in self:
            picking_type = container.picking_type_id
            location_dest = picking_type.default_location_dest_id
            for picking in container.moves2stock_ids.picking_id:
                picking.write({"location_dest_id": location_dest.id})
                moves = self.env["stock.move"]
                for move in picking.move_ids_without_package:
                    if move.state not in ["cancel", "done"]:
                        moves |= move
                moves.write({"location_dest_id": location_dest.id})
                move_lines = self.env["stock.move.line"]
                for move_line in picking.move_line_ids_without_package:
                    if move_line.state not in ["cancel", "done"]:
                        move_lines |= move_line
                move_lines.write({"location_dest_id": location_dest.id})
                picking.message_post(
                    body=_(
                        "Ubicación destino modificada desde el contenedor {}"
                    ).format(self.display_name)
                )

    def _compute_volume(self):
        for container in self:
            container.volume = sum(move.volume for move in container.moves2transit_ids)

    name = fields.Char(string="Contenedor", required=True, tracking=True)
    size_id = fields.Many2one("container.planning.size", "Capacidad", tracking=True)
    product_quantity = fields.Integer(
        string="Cantidad de productos",
        compute="_compute_product_quantity",
        help="Unidades totales de la demanda de los productos a tránsito",
    )
    date = fields.Date(string="Fecha de descarga", tracking=True)
    real_packages = fields.Integer(string="Bultos reales", tracking=True)
    departure_date = fields.Date(string="Fecha de salida", tracking=True)
    arrival_date = fields.Date(string="Fecha de llegada", tracking=True)
    incidents = fields.Text(string="Observaciones")
    state = fields.Selection(
        selection=[
            ("cancel", "Cancelado"),
            ("draft", "Borrador"),
            ("embarked", "Embarcado"),
            ("onport", "En puerto"),
            ("dispatched", "Despachado"),
            ("confirmed", "Confirmado"),
            ("download", "Descargado"),
        ],
        string="Estado",
        tracking=True,
        readonly=True,
        default="draft",
    )
    picking_ids = fields.One2many(
        comodel_name="stock.picking",
        inverse_name="container_id",
        string="Albaranes",
        copy=True,
    )
    product_id = fields.Many2one(
        comodel_name="product.product",
        string="Producto",
        related="picking_ids.move_ids.product_id",
    )
    priority = fields.Selection(
        selection=[("low", "Baja"), ("medium", "Media"), ("high", "Alta")],
        string="Prioridad",
        default="low",
        tracking=True,
    )
    purchase_id = fields.Many2one(
        comodel_name="purchase.order",
        string="Pedido compra",
        related="picking_ids.purchase_id",
        help="Campo técnico para poder buscar por pedido de compra",
    )
    moves2transit_ids = fields.Many2many(
        comodel_name="stock.move",
        relation="container_planning_moves2transit_rel",
        column1="container_id",
        column2="move_id",
        compute="_compute_moves",
        string="Productos a tránsito",
    )
    moves2stock_ids = fields.Many2many(
        comodel_name="stock.move",
        relation="container_planning_moves2stock_rel",
        column1="container_id",
        column2="move_id",
        compute="_compute_moves",
        string="Productos a existencias",
    )
    regularization_ids = fields.One2many(
        comodel_name="container.planning.regularization",
        inverse_name="container_id",
        string="Regularizaciones",
    )
    regularization_picking_ids = fields.Many2many(
        comodel_name="stock.picking",
        relation="container_planning_reg_picking_rel",
        column1="container_id",
        column2="picking_id",
        compute="_compute_pickings",
        string="Albaranes regularizaciones",
    )
    ship_name = fields.Char(string="Nombre barco", tracking=True)
    shipping_partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Naviera",
        tracking=True,
        domain="[('type', '=', 'shipping_company')]",
    )
    freight_forwarder_partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Transitario",
        tracking=True,
        domain="[('type', '=', 'freight_forwarder')]",
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        default=lambda self: self.env.company,
    )
    picking_type_id = fields.Many2one(
        "stock.picking.type",
        "Tipo de operación recepción",
        domain="[('container_manual_location_dest', '=', True)]",
        compute="_compute_picking_type",
        inverse="_inverse_picking_type",
        store=True,
        help="Por defecto es el tipo de operación de los albaranes a existencias. En "
        "caso de modificar este tipo de operación, se actualizará también en los "
        "movimientos pendientes a existencias",
    )
    volume = fields.Float(
        string="Volumen total",
        compute="_compute_volume",
        digits="Volume",
        help="Volumen total de los productos a tránsito",
    )
    company_currency_id = fields.Many2one(
        comodel_name="res.currency",
        store=True,
        related="company_id.currency_id",
        string="Moneda compañía",
    )
    usd_currency_id = fields.Many2one(
        comodel_name="res.currency",
        string="Moneda $",
        readonly=True,
        default=lambda self: self.env.ref("base.USD"),
    )
    cost_usd = fields.Monetary(
        string="Coste de mercancía ($)",
        readonly=True,
        currency_field="usd_currency_id",
        help="Subtotal de los productos a tránsito en la moneda de los pedidos de "
        "compra",
    )
    cost_eur = fields.Monetary(
        string="Coste de mercancía (€)",
        readonly=True,
        currency_field="company_currency_id",
        help="Subtotal de los productos a tránsito multiplicado por la tasa de "
        "cambio",
    )
    customs_fees = fields.Monetary(
        string="Aranceles",
        readonly=True,
        currency_field="company_currency_id",
        help="Coste de mercancía en € multiplicado por el coste de arancel del "
        "código intrastat del producto",
    )
    total_cost = fields.Monetary(
        string="Coste total",
        readonly=True,
        currency_field="company_currency_id",
        help="Suma de coste de mercancía (€) + Coste de transporte (€) + Aranceles",
    )
    currency_rate = fields.Float(string="Tasa de cambio", default=1)
    transport_cost = fields.Monetary(
        string="Coste de transporte (€)", currency_field="company_currency_id"
    )
    bank_expenses = fields.Float("Gastos bancarios (%)")

    @api.constrains("picking_ids")
    def _check_picking_types(self):
        for cnt in self:
            if len(cnt.picking_ids.picking_type_id) > 1:
                raise ValidationError(
                    _("Todos los albaranes de un contenedor deben tener el mismo tipo")
                )
            if (
                len(cnt.picking_ids.move_ids.move_dest_ids.picking_id.picking_type_id)
                > 1
            ):
                raise ValidationError(
                    _("Todos los albaranes de un contenedor deben tener el mismo tipo")
                )

    def action_update_cost(self):
        self.ensure_one()
        moves2transit = self.moves2transit_ids
        volume = sum(move.volume for move in moves2transit)
        moves2transit._update_container_cost_values(volume, self.transport_cost)
        cost_usd = sum(move.cost_usd for move in moves2transit)
        cost_eur = sum(move.cost_eur for move in moves2transit)
        customs_fees = sum(move.customs_fees for move in moves2transit)
        self.write(
            {
                "cost_usd": cost_usd,
                "cost_eur": cost_eur,
                "customs_fees": customs_fees,
                "total_cost": self.transport_cost + cost_eur + customs_fees,
            }
        )
        return True

    def _get_moves(self):
        moves2transit = self.env["stock.move"]
        moves2stock = self.env["stock.move"]
        for picking in self.picking_ids:
            for move in picking.move_ids:
                moves2transit |= move
                for move_dest in move.move_dest_ids:
                    if move.location_id == move_dest.location_dest_id:
                        # Devolución
                        continue
                    moves2stock |= move_dest
        moves2transit = moves2transit.sorted(lambda m: m.product_id)
        moves2stock = moves2stock.sorted(lambda m: m.product_id)
        return {"transit": moves2transit, "stock": moves2stock}

    def _get_forced_moves(self):
        return self.env["stock.move"].search([("force_container_id", "in", self.ids)])

    def action2dispatched(self):
        return self.write({"state": "dispatched"})

    def action2confirmed(self):
        self.write({"state": "confirmed"})
        self.action_create_batch()
        return True

    def action2download(self):
        return self.write({"state": "download"})

    def action2cancel(self):
        return self.write({"state": "cancel"})

    def action_back2embarked(self):
        return self.write({"state": "embarked"})

    def action2embarked(self):
        return self.write({"state": "embarked"})

    def action2onport(self):
        return self.write({"state": "onport"})

    def action_back2draft(self):
        if any(move.state == "done" for move in self.moves2stock_ids):
            raise exceptions.UserError(
                _(
                    "No puedes volver el contenedor a borrador si alguna de las lineas "
                    "a existencias está realizada"
                )
            )
        self._action_batch_back2draft()
        return self.write({"state": "draft"})

    def _update_transit_move_dest(self, transit_move, dest_move):
        other_moves = self.env["stock.move"]
        for move in transit_move.move_dest_ids:
            if move != dest_move:
                other_moves |= move
        if other_moves:
            transit_move.move_dest_ids = [(3, move.id) for move in other_moves]
        return True

    def _filter_pending_moves(self, moves=None):
        for move in moves or self.env["stock.move"]:
            if move.state in ["cancel", "done"]:
                moves -= move
        return moves

    def _get_transit_dest_move(self, pending_moves, transit_move):
        moves = self.env["stock.move"]
        for move in transit_move.move_dest_ids:
            if move in pending_moves and move.picking_id.state not in [
                "cancel",
                "done",
            ]:
                moves |= move
        return moves

    def _get_transit_done_move(self, transit_move):
        done_move = self.env["stock.move"]
        for move in transit_move.move_dest_ids:
            if move.state == "done":
                done_move |= move
        return done_move

    def _do_transfer_all(self):
        self.ensure_one()
        pending_moves = self._filter_pending_moves(self.moves2stock_ids)
        if pending_moves:
            pickings_clean = self.env["stock.picking"]
            pickings2transfer = self.env["stock.picking"]
            for transit_move in self.moves2transit_ids:
                if transit_move.state == "done":
                    dest_move = self._get_transit_dest_move(pending_moves, transit_move)
                    if dest_move:
                        dest_move = dest_move[0] if len(dest_move) > 1 else dest_move
                        self._update_transit_move_dest(transit_move, dest_move)
                        if dest_move.picking_id not in pickings_clean:
                            for line in dest_move.picking_id.move_ids:
                                line.move_line_ids.write({"quantity": 0})
                            pickings_clean |= dest_move.picking_id
                        pickings2transfer |= dest_move.picking_id
                        for line in transit_move.move_line_ids:
                            vals = dest_move._prepare_move_line_vals()
                            vals.update({"quantity": line.quantity})
                            if line.result_package_id:
                                vals.update(
                                    {
                                        "package_id": line.result_package_id.id,
                                        "result_package_id": line.result_package_id.id,
                                    }
                                )
                            if line.lot_id:
                                vals.update({"lot_id": line.lot_id.id})
                            self.env["stock.move.line"].create(vals)
            for picking in pickings2transfer:
                for move in picking.move_ids:
                    if move.exists() and move.state not in ["cancel", "done"]:
                        move._merge_moves()
                res = picking.with_context(
                    skip_immediate=True, skip_backorder=True
                ).button_validate()
                if res and isinstance(res, dict) and res.get("res_model"):
                    ctx = res.get("context", {})
                    backorder_confirm = (
                        self.env[res["res_model"]].with_context(ctx).create({})
                    )
                    backorder_confirm.with_context(ctx).process()
        for transit_move in self.moves2transit_ids:
            if transit_move.state == "done":
                done_move = self._get_transit_done_move(transit_move)
                self._update_transit_move_dest(transit_move, done_move)
        return True

    def action_done_all(self):
        for container in self:
            container._do_transfer_all()
        return True

    def _update_moves_date(self, new_date, moves):
        new_date = fields.Datetime.to_datetime(new_date).replace(hour=6, minute=00)
        new_moves = self.env["stock.move"]
        for move in moves:
            if move.state not in ["cancel", "done"]:
                new_moves |= move
        new_moves.write({"date": new_date, "date_deadline": new_date})
        new_moves.picking_id.with_context(
            force_sched_date_recalc=True
        )._compute_scheduled_date()
        return True

    @api.model_create_multi
    def create(self, vals_list):
        containers = super().create(vals_list)
        for container, vals in zip(containers, vals_list, strict=False):
            new_date = vals.get("date", False) or vals.get("arrival_date", False)
            if new_date:
                self._update_moves_date(new_date, container.moves2stock_ids)
        return containers

    def write(self, vals):
        for container in self:
            new_date = vals.get("date", container.date) or vals.get(
                "arrival_date", False
            )
            if new_date:
                self._update_moves_date(new_date, self.moves2stock_ids)
        res = super().write(vals)
        if any(
            key in vals for key in ["transport_cost", "currency_rate", "bank_expenses"]
        ):
            for container in self:
                container.action_update_cost()
        return res

    def action_create_batch(self):
        for container in self:
            container._create_batch()
        return True

    def _create_batch(self):
        self.ensure_one()
        pickings = self.moves2stock_ids.picking_id
        picking_type = pickings.picking_type_id
        if len(picking_type) != 1:
            raise exceptions.UserError(
                _(
                    "No se puede crear una agrupación de albaranes si todos los "
                    "albaranes no tienen el mismo tipo de operación"
                )
            )
        batch = self.env["stock.picking.batch"].create(
            {
                "picking_ids": pickings.ids,
                "scheduled_date": self.date,
                "picking_type_id": picking_type.id,
                "container_id": self.id,
                "name": _("Contenedor {}").format(self.name),
                "state": "in_progress",
            }
        )
        batch.message_post_with_source(
            "mail.message_origin_link",
            render_values={"self": batch, "origin": self},
            subtype_xmlid="mail.mt_note",
        )
        return batch

    def _action_batch_back2draft(self):
        for container in self:
            container._batch_back2draft()
        return True

    def _batch_back2draft(self):
        self.ensure_one()
        batch = self.env["stock.picking.batch"].search([("container_id", "=", self.id)])
        if batch:
            batch.action_cancel()
            batch.action_back_to_draft()
            batch.unlink()
        return True

    def _create_container_planning_line(self):
        planning_line_obj = self.env["container.planning.line"]
        vals = []
        if not self.env.company.is_active_container_planning_line:
            return
        for container in self:
            planning_line_delete_container = planning_line_obj.search(
                [
                    ("move_transit_id", "not in", container.moves2transit_ids.ids),
                    ("container_id", "=", container.id),
                ]
            )
            if planning_line_delete_container:
                planning_line_delete_container.write(
                    {"container_id": self.env["container.planning"]}
                )
            for transit in container.moves2transit_ids:
                qty_done_stock = sum(
                    transit.move_dest_ids.filtered(
                        lambda x, transit=transit: x.product_id == transit.product_id
                        and x.location_dest_id.usage != "supplier"
                    ).mapped("quantity")
                )
                planning_line = planning_line_obj.search(
                    [("move_transit_id", "=", transit.id)]
                )
                if not planning_line:
                    vals.append(
                        {
                            "container_id": container.id,
                            "product_id": transit.product_id.id,
                            "purchase_id": transit.purchase_id.id,
                            "product_uom_qty": transit.product_uom_qty,
                            "qty_done_transit": transit.quantity,
                            "qty_done_stock": qty_done_stock,
                            "pending_qty": transit.quantity - qty_done_stock,
                            "picking_id": transit.picking_id.id,
                            "move_transit_id": transit.id,
                        }
                    )
                    continue
                planning_line.write(
                    {
                        "product_uom_qty": transit.product_uom_qty,
                        "qty_done_stock": qty_done_stock,
                        "qty_done_transit": transit.quantity,
                        "pending_qty": transit.quantity - qty_done_stock,
                        "picking_id": transit.picking_id.id,
                        "container_id": container.id,
                        "move_transit_id": transit.id,
                    }
                )
                if planning_line_delete_container:
                    pick_backorder_id = self.env["stock.picking"].search(
                        [
                            ("backorder_id", "=", transit.picking_id.id),
                        ],
                        limit=1,
                    )
                    planning_line_delete_container.write(
                        {"picking_id": pick_backorder_id.id}
                    )
        if vals:
            planning_line_obj.create(vals)
