# Copyright 2025 Process Control
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import _, fields, models, tools
from odoo.exceptions import UserError


class StockLandedCost(models.Model):
    _inherit = "stock.landed.cost"

    def compute_landed_cost(self):
        res = super().compute_landed_cost()
        for cost in self:
            rounding = cost.currency_id.rounding
            for line in cost.cost_lines:
                if line.split_method != "by_intrastat":
                    continue
                total2split = 0
                value_split = 0
                total_line = 0
                for valuation in cost.valuation_adjustment_lines:
                    if valuation.cost_line_id == line:
                        if not valuation.product_id.intrastat_code_id:
                            raise UserError(
                                _(
                                    "Error: El producto %(name)s no tiene definido un código"
                                    " arancelario, revíselo.",
                                    name=valuation.product_id.display_name,
                                )
                            )
                        if (
                            valuation.product_id.intrastat_code_id.has_cost_percent
                            and not valuation.product_id.intrastat_code_id.cost_percent
                        ):
                            raise UserError(
                                _(
                                    "Error: El código arancelario %(code)s no tiene definido "
                                    "un %% de arancel, revíselo. Si el porcentaje "
                                    "arancelario es 0, no se debe marcar la casilla "
                                    "'Tiene %% de arancel' en el código arancelario.",
                                    code=valuation.product_id.intrastat_code_id.display_name,
                                )
                            )
                        total2split += (
                            valuation.former_cost * valuation.intrastat_percent
                        )
                        if valuation.intrastat_percent != 0:
                            total_line += 1

                for valuation in cost.valuation_adjustment_lines:
                    if valuation.cost_line_id and valuation.cost_line_id.id == line.id:
                        if (
                            total2split
                            and valuation.product_id.intrastat_code_id.cost_percent
                        ):
                            line_val = (
                                valuation.former_cost * valuation.intrastat_percent
                            )
                            value = (line.price_unit / total2split) * line_val
                        else:
                            value = line.price_unit / (total_line or 1)

                        if valuation.intrastat_percent != 0:
                            if rounding:
                                value = tools.float_round(
                                    value,
                                    precision_rounding=rounding,
                                    rounding_method="UP",
                                )
                                fnc = min if line.price_unit > 0 else max
                                value = fnc(value, line.price_unit - value_split)
                                value_split += value
                            valuation.write({"additional_landed_cost": value})
                        else:
                            valuation.write({"additional_landed_cost": 0})

        return res


class StockLandedCostLine(models.Model):
    _inherit = "stock.landed.cost.lines"

    split_method = fields.Selection(
        selection_add=[("by_intrastat", "Por código arancelario")],
        ondelete={"by_intrastat": "cascade"},
    )


class AdjustmentLines(models.Model):
    _inherit = "stock.valuation.adjustment.lines"

    intrastat_percent = fields.Float(
        string="% de arancel",
        related="product_id.intrastat_code_id.cost_percent",
    )
