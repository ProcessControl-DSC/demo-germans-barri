# Copyright 2025 Process Control
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import fields, models


class PurchaseReport(models.Model):
    _inherit = "purchase.report"

    qty_pending = fields.Float(string="Cantidad pendiente", readonly=True)
    pending_amount = fields.Float(string="Importe pendiente", readonly=True)

    def _select(self):
        res = super()._select()
        res += ", l.qty_pending, l.pending_amount"
        return res

    def _group_by(self):
        res = super()._group_by()
        res += ", l.qty_pending, l.pending_amount"
        return res
