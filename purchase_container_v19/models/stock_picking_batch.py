# Copyright 2025 Process Control
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import _, exceptions, fields, models


class StockPickingBatch(models.Model):
    _inherit = "stock.picking.batch"

    container_id = fields.Many2one(
        comodel_name="container.planning", string="Contenedor"
    )

    def action_cancel(self):
        if sum(ml.quantity for ml in self.move_line_ids) > 0:
            raise exceptions.UserError(
                _(
                    "Solo puede cancelar agrupaciones que no tengan ninguna "
                    "cantidad realizada"
                )
            )
        return super().action_cancel()

    def action_back_to_draft(self):
        for batch in self:
            if batch.state != "cancel":
                raise exceptions.UserError(
                    _(
                        "Solo puede cambiar a borrador agrupaciones con el estado "
                        "en progreso o cancelado"
                    )
                )
        self.write({"state": "draft"})
        return True
