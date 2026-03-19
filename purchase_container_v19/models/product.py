# Copyright 2025 Process Control
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from psycopg2.extensions import AsIs

from odoo import fields, models


class ProductProduct(models.Model):
    _inherit = "product.product"

    def _query_qty_transit(self):
        query = """
            SELECT sum(quantity)
            FROM stock_quant q
                INNER JOIN stock_location l on l.id = q.location_id
            WHERE l.usage = 'transit'
                AND q.product_id = %s
                AND l.company_id = {}""".format(
            self.env.context.get("force_sql_company", self.env.company.id)
        )
        wh_ids = self.env.context.get("sql_warehouse_ids", [])
        if len(wh_ids) == 1:
            query = f"{query} AND l.warehouse_id = {wh_ids[0]}"
        elif len(wh_ids) > 1:
            query = "{} AND l.warehouse_id IN {}".format(
                query, tuple(self.env.context["sql_warehouse_ids"])
            )
        return query

    def _query_qty_supplier(self):
        query = """
            SELECT sum(product_uom_qty)
            FROM stock_move m
                INNER JOIN stock_location l on l.id = m.location_id
                INNER JOIN stock_location ld on ld.id = m.location_dest_id
            WHERE product_id = %s
                AND state NOT IN ('draft', 'cancel', 'done')
                AND l.usage = 'supplier'
                AND ld.usage IN ('transit', 'internal', 'view')
                AND m.company_id = {}""".format(
            self.env.context.get("force_sql_company", self.env.company.id)
        )
        wh_ids = self.env.context.get("sql_warehouse_ids", [])
        if len(wh_ids) == 1:
            query = f"{query} AND ld.warehouse_id = {wh_ids[0]}"
        elif len(wh_ids) > 1:
            query = "{} AND ld.warehouse_id IN {}".format(
                query, tuple(self.env.context["sql_warehouse_ids"])
            )
        return query

    def _query_next_date(self):
        query = """
            SELECT SUM(m.product_uom_qty), m.date::date
            FROM stock_move m
                INNER JOIN stock_location l on l.id = m.location_id
                INNER JOIN stock_location ld on ld.id = m.location_dest_id
            WHERE product_id = %s AND product_uom_qty > 0
                AND state NOT IN ('draft', 'cancel', 'done')
                AND l.usage IN {}
                AND ld.usage IN ('internal', 'view')
                AND m.company_id = {}""".format(
            tuple(self._get_in_usages()),
            self.env.context.get("force_sql_company", self.env.company.id),
        )
        wh_ids = self.env.context.get("sql_warehouse_ids", [])
        if len(wh_ids) == 1:
            query = f"{query} AND ld.warehouse_id = {wh_ids[0]}"
        elif len(wh_ids) > 1:
            query = "{} AND ld.warehouse_id IN {}".format(
                query, tuple(self.env.context["sql_warehouse_ids"])
            )
        query = f"""{query} GROUP BY m.date::date
            ORDER BY m.date::date ASC"""
        return query

    def _query_qty_pretransit(self):
        return """
            SELECT SUM(pol.product_uom_qty)
            FROM purchase_order as po
                INNER JOIN purchase_order_line as pol on po.id = pol.order_id
            WHERE product_id = %s
                AND po.state NOT IN ('purchase', 'cancel', 'done')
                AND po.company_id = {}""".format(
            self.env.context.get("force_sql_company", self.env.company.id)
        )

    def _get_product_qtys_dict(self):
        res = super()._get_product_qtys_dict()
        self._cr.execute(self._query_qty_transit(), [self.id])
        transit = self._cr.fetchone()
        transit = transit[0] if transit and transit[0] else 0
        self._cr.execute(self._query_qty_pretransit(), [self.id])
        pretransit = self._cr.fetchone()
        pretransit = pretransit[0] if pretransit and pretransit[0] else 0
        self._cr.execute(self._query_qty_supplier(), [self.id])
        supplier = self._cr.fetchone()
        supplier = supplier[0] if supplier and supplier[0] else 0
        self._cr.execute(self._query_next_date(), [self.id])
        next_input_qty = 0
        next_input_date = False
        next_input_data = self._cr.fetchone()
        if next_input_data:
            next_input_qty = next_input_data[0]
            next_input_date = next_input_data[1]
        res.update(
            {
                "qty_intransit": transit,
                "qty_incoming_intransit": supplier,
                "qty_real_available": res["qty_real_available"] + transit + supplier,
                "next_input_qty": next_input_qty,
                "next_input_date": next_input_date,
                "qty_preincoming": pretransit,
            }
        )
        return res

    def get_stock_from_location(self, location):
        result = super().get_stock_from_location(location)
        supplier_moves = self.env["stock.move"].search(
            [
                ("product_id", "=", self.id),
                ("state", "not in", ["draft", "cancel", "done"]),
                ("location_id.usage", "=", "supplier"),
                ("location_dest_id.usage", "in", ["transit", "view", "internal"]),
                ("location_dest_id", "child_of", location.id),
            ],
            order="date asc",
        )
        transit_moves = self.env["stock.move"].search(
            [
                ("product_id", "=", self.id),
                ("state", "not in", ["draft", "cancel", "done"]),
                ("location_id.usage", "=", "transit"),
                ("location_id", "child_of", location.id),
                ("location_dest_id.usage", "in", ["view", "internal"]),
            ],
            order="date asc",
        )
        next_input_qty = 0
        next_input_date = False
        for m in transit_moves:
            if m.product_uom_qty > 0:
                next_input_qty = m.product_uom_qty
                next_input_date = m.date
                break
        quants = self.env["stock.quant"].search(
            [
                ("product_id", "=", self.id),
                ("location_id.usage", "=", "transit"),
                ("location_id", "child_of", location.id),
            ]
        )
        qty_intransit = sum(q.quantity for q in quants)
        qty_incoming_intransit = sum(m.product_uom_qty for m in supplier_moves)
        qty_real_available = result["qty_real_available"] + qty_intransit
        result.update(
            {
                "qty_real_available": qty_real_available,
                "qty_intransit": round(qty_intransit, 2),
                "qty_incoming_intransit": round(qty_incoming_intransit, 2),
                "next_input_qty": round(next_input_qty, 2),
                "next_input_date": next_input_date,
            }
        )
        return result

    def _query_search_qty_intransit(self):
        return """
            SELECT q.product_id
            FROM stock_quant q INNER JOIN stock_location l on l.id = q.location_id
            WHERE l.usage = 'transit'
            AND l.company_id = {}
            GROUP BY product_id
            HAVING sum(quantity) %s %s""".format(
            self.env.context.get("force_sql_company", self.env.company.id)
        )

    def _query_search_qty_preincoming(self):
        return """
            SELECT pol.product_id
            FROM purchase_order_line as pol
                INNER JOIN purchase_order as po on po.id = pol.order_id
            WHERE po.state NOT IN ('purchase', 'cancel', 'done')
                AND po.company_id = {}
            GROUP BY pol.product_id
            HAVING sum(pol.product_uom_qty) %s %s""".format(
            self.env.context.get("force_sql_company", self.env.company.id)
        )

    def _query_search_qty_incoming_intransit(self):
        return """
            SELECT product_id
            FROM stock_move m
                INNER JOIN stock_location l on l.id = m.location_id
                INNER JOIN stock_location ld on ld.id = m.location_dest_id
            WHERE state NOT IN ('draft', 'cancel', 'done')
                AND l.usage = 'supplier'
                AND ld.usage IN ('transit', 'view', 'internal')
                AND m.company_id = {}
            GROUP BY product_id
            HAVING sum(product_uom_qty) %s %s""".format(
            self.env.context.get("force_sql_company", self.env.company.id)
        )

    def _search_qty_intransit(self, operator, value):
        return self._search_by_operator("qty_intransit", operator, value)

    def _search_qty_incoming_intransit(self, operator, value):
        return self._search_by_operator("qty_incoming_intransit", operator, value)

    def _search_qty_preincoming(self, operator, value):
        return self._search_by_operator("qty_preincoming", operator, value)

    def _search_next_input_date(self, operator, value):
        final_operator = "in"
        if operator in ("=", "!=") and not value:
            if operator == "=":
                final_operator = "not in"
            operator = "is not"
            value = AsIs("null")
        query = """
            SELECT product_id
            FROM (
                SELECT DISTINCT ON (m.product_id) m.product_id, m.date::date
                FROM stock_move m
                    INNER JOIN stock_location l on l.id = m.location_id
                    INNER JOIN stock_location ld on ld.id = m.location_dest_id
                WHERE product_uom_qty > 0
                    AND state NOT IN ('draft', 'cancel', 'done')
                        AND l.usage IN %s
                    AND ld.usage IN ('internal', 'view')
                    AND m.company_id = %s
                ORDER BY m.product_id, m.date
            ) AS sub
            WHERE date %s %s"""
        self._cr.execute(
            query,
            [
                tuple(self._get_in_usages()),
                self.env.context.get("force_sql_company", self.env.company.id),
                AsIs(operator),
                value,
            ],
        )
        res = [x[0] for x in self._cr.fetchall()]
        return [("id", final_operator, res)]

    qty_intransit = fields.Float(
        "Tránsito", compute="_compute_product_qtys", search="_search_qty_intransit"
    )
    qty_incoming_intransit = fields.Float(
        "Comprada",
        compute="_compute_product_qtys",
        search="_search_qty_incoming_intransit",
    )
    next_input_qty = fields.Float(
        "Cantidad próxima recepción", compute="_compute_product_qtys"
    )
    qty_preincoming = fields.Float(
        "Perspectiva compra",
        compute="_compute_product_qtys",
        search="_search_qty_preincoming",
    )
    next_input_date = fields.Date(
        "Próxima recepción",
        compute="_compute_product_qtys",
        search="_search_next_input_date",
    )

    def get_stock_from_date(self, date):
        res = super().get_stock_from_date(date)
        query = """
            SELECT sum(product_uom_qty)
            FROM stock_move m
                INNER JOIN stock_location l on l.id = m.location_id
                INNER JOIN stock_location ld on ld.id = m.location_dest_id
            WHERE product_id = %s
                AND state NOT IN ('draft', 'cancel', 'done')
                AND l.usage = 'transit'
                AND ld.usage in ('view', 'internal')
                AND date <= %s
                AND m.company_id = %s"""
        self._cr.execute(
            query,
            [
                self.id,
                res["date"],
                self.env.context.get("force_sql_company", self.env.company.id),
            ],
        )
        transit = self._cr.fetchone()
        transit = transit and transit[0] or 0
        res.update(
            {
                "qty_intransit": transit,
                "qty_incoming_intransit": 0,
                "qty_real_available": res["qty_real_available"] + transit,
            }
        )
        return res

    def _get_in_usages(self):
        return ["supplier", "transit"]
