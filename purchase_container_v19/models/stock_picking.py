# Copyright 2025 Process Control
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = "stock.picking"

    @api.depends("move_ids.state", "move_ids.date", "move_type")
    def _compute_scheduled_date(self):
        pickings = self
        for picking in self:
            if picking.forced_scheduled_date and not self.env.context.get(
                "force_sched_date_recalc", False
            ):
                pickings -= picking
        super(StockPicking, pickings)._compute_scheduled_date()

    container_number = fields.Integer(string="Container number", copy=False)
    container_id = fields.Many2one(
        comodel_name="container.planning", string="Contenedor", copy=False
    )
    force_container_id = fields.Many2one(
        comodel_name="container.planning",
        string="Forzar contenedor líneas",
        help="Si seleccionas algún contenedor, se actualizará automáticamente en "
        "los movimientos de este albarán",
    )
    location_dest_usage = fields.Selection(
        string="Tipo de ubicación de destino", related="location_dest_id.usage"
    )
    forced_scheduled_date = fields.Boolean(
        string="Fecha prevista forzada",
        help="Se usa para evitar que se recalcule la fecha prevista de un albarán una"
        " vez que se ha forzado desde algún cálculo",
    )

    def write(self, vals):
        res = super().write(vals)
        if not self.env.company.is_active_container_planning_line:
            return res
        if "container_id" in vals and not self.container_id:
            planning_line = self.env["container.planning.line"].search(
                [("picking_id", "in", self.ids)]
            )
            if planning_line:
                planning_line.write({"container_id": self.env["container.planning"]})
            return res
        if self.container_id:
            self.container_id._create_container_planning_line()
        else:
            for move in self.move_ids.move_orig_ids:
                move.container_id._create_container_planning_line()
                break
        return res

    @api.constrains("container_id")
    def _check_container_picking_types(self):
        self.container_id._check_picking_types()

    def _action_done(self):
        for picking in self:
            p_type = picking.picking_type_id
            if (
                p_type.code == "incoming"
                and picking.location_dest_id.usage == "transit"
                and picking.location_dest_id.container_required
                and picking.location_id.usage == "supplier"
                and not picking.container_id
            ):
                raise UserError(
                    _(
                        "Para poder transferir el albarán {} debes establecerle un "
                        "contenedor. De lo contrario debes desactivar el campo "
                        "'Contenedor requerido' de la ubicación {}"
                    ).format(picking.name, picking.location_dest_id.name)
                )
        return super()._action_done()

    def _create_backorder(self):
        backorders = super()._create_backorder()
        for pick in backorders:
            if pick.forced_scheduled_date:
                pick.with_context(
                    force_sched_date_recalc=True
                )._compute_scheduled_date()
        return backorders

    def _split_picking_dest(self):
        pickings = super()._split_picking_dest()
        for picking in pickings:
            if picking.forced_scheduled_date:
                picking.with_context(
                    force_sched_date_recalc=True
                )._compute_scheduled_date()
        return pickings
