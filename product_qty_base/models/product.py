# Copyright 2025 Process Control
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from datetime import datetime

from psycopg2.extensions import AsIs

from odoo import fields, models


class ProductProduct(models.Model):
    _inherit = "product.product"

    standard_price = fields.Float(tracking=True)

    def _query_qty_real_select(self):
        return "SELECT sum(quantity)"

    def _query_qty_real_from(self):
        return """
        FROM stock_quant q
        INNER JOIN stock_location l on l.id = q.location_id
        INNER JOIN stock_warehouse sw on sw.id = l.warehouse_id
        """

    def _query_qty_real_where(self):
        query = """
        WHERE l.usage = 'internal'
        AND sw.consider_stock IS TRUE
        AND l.scrap_location IS FALSE
        AND (l.exclude_stock IS FALSE or l.exclude_stock IS NULL)
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

    def _query_qty_real(self):
        query = "{} {} {}".format(
            self._query_qty_real_select(),
            self._query_qty_real_from(),
            self._query_qty_real_where(),
        )
        return query

    def _query_qty_reserved_select(self):
        return "SELECT sum(m.product_uom_qty)"

    def _query_qty_reserved_from(self):
        return """
        FROM stock_move m
        INNER JOIN stock_location l on l.id = m.location_id
        INNER JOIN stock_warehouse sw on sw.id = l.warehouse_id
        INNER JOIN stock_location ld on ld.id = m.location_dest_id
        LEFT JOIN stock_warehouse swld on swld.id = ld.warehouse_id
        """

    def _query_qty_reserved_where(self):
        query = """
            WHERE m.product_id = %s
            AND l.company_id = {}
            AND m.state NOT IN ('draft', 'cancel', 'done')
            AND (
                (
                    l.usage IN ('internal', 'view')
                    AND ld.usage IN ('customer', 'production', 'samples', 'transit')
                    AND (sw.consider_stock IS TRUE AND l.scrap_location IS FALSE)
                    AND (l.exclude_stock IS FALSE OR l.exclude_stock IS NULL)
                )
                OR (
                    l.usage = 'internal' AND ld.usage = 'internal'
                    AND (
                        sw.consider_stock IS TRUE
                        AND (l.exclude_stock IS FALSE OR l.exclude_stock IS NULL)
                        AND (swld.consider_stock IS FALSE OR ld.exclude_stock IS TRUE)
                    )
                )
            )""".format(self.env.context.get("force_sql_company", self.env.company.id))
        wh_ids = self.env.context.get("sql_warehouse_ids", [])
        if len(wh_ids) == 1:
            query = f"{query} AND l.warehouse_id = {wh_ids[0]}"
        elif len(wh_ids) > 1:
            query = "{} AND l.warehouse_id IN {}".format(
                query, tuple(self.env.context["sql_warehouse_ids"])
            )
        return query

    def _query_qty_reserved(self):
        query = "{} {} {}".format(
            self._query_qty_reserved_select(),
            self._query_qty_reserved_from(),
            self._query_qty_reserved_where(),
        )
        return query

    def _query_qty_returned_select(self):
        return "SELECT sum(product_uom_qty)"

    def _query_qty_returned_from(self):
        return """
        FROM stock_move m
        INNER JOIN stock_location l on l.id = m.location_id
        INNER JOIN stock_location ld on ld.id = m.location_dest_id
        INNER JOIN stock_warehouse sw on sw.id = ld.warehouse_id
        """

    def _query_qty_returned_where(self):
        """Si tenemos instalado el módulo 'product_qty_container', no contemplar
        la opción 'supplier', ya que ese módulo ya lo hace, entonces para los campos
        'Otras entradas previstas' y 'Disponible' se están sumando dos veces las
        cantidades de los movimientos de proveedores a existencias"""
        lusages = ["customer", "production", "samples"]
        if not self._fields.get("next_input_date"):
            lusages.append("supplier")
        query = """
        WHERE product_id = %s
        AND state NOT IN ('draft', 'cancel', 'done')
        AND l.usage IN {}
        AND ld.usage IN ('internal', 'view')
        AND m.company_id = {}
        AND sw.consider_stock IS TRUE
        AND l.scrap_location IS FALSE
        AND (ld.exclude_stock IS FALSE or ld.exclude_stock IS NULL)""".format(
            tuple(lusages),
            self.env.context.get("force_sql_company", self.env.company.id),
        )
        wh_ids = self.env.context.get("sql_warehouse_ids", [])
        if len(wh_ids) == 1:
            query = f"{query} AND ld.warehouse_id = {wh_ids[0]}"
        elif len(wh_ids) > 1:
            query = "{} AND ld.warehouse_id IN {}".format(
                query, tuple(self.env.context["sql_warehouse_ids"])
            )
        return query

    def _query_qty_returned(self):
        query = "{} {} {}".format(
            self._query_qty_returned_select(),
            self._query_qty_returned_from(),
            self._query_qty_returned_where(),
        )
        return query

    def _query_qty_production_select(self):
        return "SELECT sum(product_uom_qty)"

    def _query_qty_production_from(self):
        return """
            FROM stock_move m
            INNER JOIN stock_location l on l.id = m.location_id
        """

    def _query_qty_production_where(self):
        query = """
            WHERE product_id = %s
            AND state NOT IN ('draft', 'cancel', 'done')
            AND l.usage IN ('production')
            AND m.company_id = {}
            AND l.scrap_location IS FALSE""".format(
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

    def _query_qty_production(self):
        query = "{} {} {}".format(
            self._query_qty_production_select(),
            self._query_qty_production_from(),
            self._query_qty_production_where(),
        )
        return query

    def _get_all_products_qtys_dict(self):
        res = {}
        for product in self:
            res[product.id] = product._get_product_qtys_dict()
        return res

    def _get_product_qtys_dict(self):
        """Almacena los datos en un diccionario antes de asignar al campo,
        ya que los cálculos de algunos campos pueden depender de otros,
        evitando calcular varias veces un mismo valor."""
        self.ensure_one()
        self._cr.execute(self._query_qty_real(), [self.id])
        quants = self._cr.fetchone()
        quants = quants and quants[0] or 0
        self._cr.execute(self._query_qty_reserved(), [self.id])
        reserved = self._cr.fetchone()
        reserved = reserved and reserved[0] or 0
        self._cr.execute(self._query_qty_returned(), [self.id])
        returned = self._cr.fetchone()
        returned = returned and returned[0] or 0
        self._cr.execute(self._query_qty_production(), [self.id])
        production = self._cr.fetchone()
        production = production and production[0] or 0
        return {
            "qty_real": quants,
            "qty_reserved": reserved,
            "qty_returned": returned,
            "qty_real_available": quants + returned - reserved,
            "qty_available_now": quants - reserved,
            "qty_production": production,
        }

    def _compute_product_qtys(self):
        res = self._get_all_products_qtys_dict()
        for product in self:
            data = res[product.id]
            for fld, value in data.items():
                product[fld] = value

    def _query_search_qty_real_select(self):
        return "SELECT q.product_id"

    def _query_search_qty_real_from(self):
        return """
        FROM stock_quant q
        INNER JOIN stock_location l on l.id = q.location_id
        INNER JOIN stock_warehouse sw on sw.id = l.warehouse_id
        """

    def _query_search_qty_real_where(self):
        return """
        WHERE l.usage = 'internal'
        AND l.company_id = {}
        AND sw.consider_stock IS TRUE
        AND l.scrap_location IS FALSE
        AND (l.exclude_stock IS FALSE or l.exclude_stock IS NULL)
        """.format(self.env.context.get("force_sql_company", self.env.company.id))

    def _query_search_qty_real_groupby(self):
        return "GROUP BY q.product_id"

    def _query_search_qty_real_having(self):
        return "HAVING sum(quantity) %s %s"

    def _query_search_qty_real(self):
        return "{} {} {} {} {}".format(
            self._query_search_qty_real_select(),
            self._query_search_qty_real_from(),
            self._query_search_qty_real_where(),
            self._query_search_qty_real_groupby(),
            self._query_search_qty_real_having(),
        )

    def _query_search_qty_reserved_select(self):
        return "SELECT product_id"

    def _query_search_qty_reserved_from(self):
        return """
        FROM stock_move m
        INNER JOIN stock_location l on l.id = m.location_id
        INNER JOIN stock_warehouse sw on sw.id = l.warehouse_id
        INNER JOIN stock_location ld on ld.id = m.location_dest_id
        LEFT JOIN stock_warehouse swld on swld.id = ld.warehouse_id
        """

    def _query_search_qty_reserved_where(self):
        return """
        WHERE state NOT IN ('draft', 'cancel', 'done')
        AND m.company_id = {}
        AND (
            (
                l.usage IN ('internal', 'view')
                AND ld.usage IN ('customer', 'production', 'samples', 'transit')
                AND sw.consider_stock IS TRUE AND l.scrap_location IS FALSE
                AND (l.exclude_stock IS FALSE OR l.exclude_stock IS NULL)
            )
            OR (
                l.usage = 'internal' AND ld.usage = 'internal'
                AND (
                    sw.consider_stock IS TRUE
                    AND (l.exclude_stock IS FALSE OR l.exclude_stock IS NULL)
                    AND (swld.consider_stock IS FALSE OR ld.exclude_stock IS TRUE)
                )
            )
        )
        """.format(self.env.context.get("force_sql_company", self.env.company.id))

    def _query_search_qty_reserved_groupby(self):
        return "GROUP BY product_id"

    def _query_search_qty_reserved_having(self):
        return "HAVING sum(product_uom_qty) %s %s"

    def _query_search_qty_reserved(self):
        return "{} {} {} {} {}".format(
            self._query_search_qty_reserved_select(),
            self._query_search_qty_reserved_from(),
            self._query_search_qty_reserved_where(),
            self._query_search_qty_reserved_groupby(),
            self._query_search_qty_reserved_having(),
        )

    def _query_search_qty_returned_select(self):
        return "SELECT product_id"

    def _query_search_qty_returned_from(self):
        return """
        FROM stock_move m
        INNER JOIN stock_location l on l.id = m.location_id
        INNER JOIN stock_location ld on ld.id = m.location_dest_id
        INNER JOIN stock_warehouse sw on sw.id = ld.warehouse_id
        """

    def _query_search_qty_returned_where(self):
        """Si tenemos instalado el módulo 'product_qty_container', no contemplar
        la opción 'supplier', ya que ese módulo ya lo hace, entonces para los campos
        'Otras entradas previstas' y 'Disponible' se están sumando dos veces las
        cantidades de los movimientos de proveedores a existencias"""
        lusages = ["customer", "production", "samples"]
        if not self._fields.get("next_input_date"):
            lusages.append("supplier")
        return """
        WHERE state NOT IN ('draft', 'cancel', 'done')
        AND m.company_id = {}
        AND l.usage IN {}
        AND ld.usage IN ('internal', 'view')
        AND sw.consider_stock IS TRUE
        AND l.scrap_location IS FALSE
        AND (ld.exclude_stock IS FALSE or ld.exclude_stock IS NULL)
        """.format(
            self.env.context.get("force_sql_company", self.env.company.id),
            tuple(lusages),
        )

    def _query_search_qty_returned_groupby(self):
        return "GROUP BY product_id"

    def _query_search_qty_returned_having(self):
        return "HAVING sum(product_uom_qty) %s %s"

    def _query_search_qty_returned(self):
        return "{} {} {} {} {}".format(
            self._query_search_qty_returned_select(),
            self._query_search_qty_returned_from(),
            self._query_search_qty_returned_where(),
            self._query_search_qty_returned_groupby(),
            self._query_search_qty_returned_having(),
        )

    def _query_search_qty_available_now_select(self):
        return "SELECT product_id"

    def _query_search_qty_available_now_groupby(self):
        return "GROUP BY q.product_id"

    def _query_search_qty_available_now_groupby_foo(self):
        return "GROUP BY foo.product_id"

    def _query_search_qty_available_now_having(self):
        return "HAVING sum(sum) %s %s"

    def _query_search_qty_available_now_select_1(self):
        return "SELECT q.product_id, sum(quantity)"

    def _query_search_qty_available_now_from_1(self):
        return """
        FROM stock_quant q
        INNER JOIN stock_location l on l.id = q.location_id
        INNER JOIN stock_warehouse sw on sw.id = l.warehouse_id
        """

    def _query_search_qty_available_now_where_1(self):
        return """
        WHERE l.usage = 'internal'
        AND l.company_id = {}
        AND sw.consider_stock IS TRUE
        AND l.scrap_location IS FALSE
        AND (l.exclude_stock IS FALSE or l.exclude_stock IS NULL)
        """.format(
            self.env.context.get("force_sql_company", self.env.company.id),
        )

    def _query_search_qty_available_now_select_2(self):
        return "SELECT product_id, sum(product_uom_qty * -1)"

    def _query_search_qty_available_now_from_2(self):
        return """
        FROM
        stock_move m
        INNER JOIN stock_location l on l.id = m.location_id
        INNER JOIN stock_warehouse sw on sw.id = l.warehouse_id
        INNER JOIN stock_location ld on ld.id = m.location_dest_id
        LEFT JOIN stock_warehouse swld on swld.id = ld.warehouse_id
        """

    def _query_search_qty_available_now_where_2(self):
        return """
        WHERE state NOT IN ('draft', 'cancel', 'done')
        AND m.company_id = {}
        AND (
            (
                l.usage IN ('internal', 'view')
                AND ld.usage IN ('customer', 'production', 'samples', 'transit')
                AND sw.consider_stock IS TRUE AND l.scrap_location IS FALSE
                AND (l.exclude_stock IS FALSE OR l.exclude_stock IS NULL)
            )
            OR (
                l.usage = 'internal' AND ld.usage = 'internal'
                AND (
                    sw.consider_stock IS TRUE
                    AND (l.exclude_stock IS FALSE OR l.exclude_stock IS NULL)
                    AND (swld.consider_stock IS FALSE OR ld.exclude_stock IS TRUE)
                )
            )
        )
        """.format(
            self.env.context.get("force_sql_company", self.env.company.id),
        )

    def _query_search_qty_available_now_groupby_2(self):
        return "GROUP BY l.usage, ld.usage, m.product_id"

    def _query_search_qty_available_now(self):
        return "{} FROM ({} {} {} {} UNION ({} {} {} {})) AS foo {} {}".format(
            self._query_search_qty_available_now_select(),
            self._query_search_qty_available_now_select_1(),
            self._query_search_qty_available_now_from_1(),
            self._query_search_qty_available_now_where_1(),
            self._query_search_qty_available_now_groupby(),
            self._query_search_qty_available_now_select_2(),
            self._query_search_qty_available_now_from_2(),
            self._query_search_qty_available_now_where_2(),
            self._query_search_qty_available_now_groupby_2(),
            self._query_search_qty_available_now_groupby_foo(),
            self._query_search_qty_available_now_having(),
        )

    def _query_search_qty_real_available_select(self):
        return "SELECT product_id"

    def _query_search_qty_real_available_groupby(self):
        return "GROUP BY product_id"

    def _query_search_qty_real_available_having(self):
        return "HAVING sum(sum) %s %s"

    def _query_search_qty_real_available_select_1(self):
        return "SELECT q.product_id, sum(quantity)"

    def _query_search_qty_real_available_from_1(self):
        return """
        FROM stock_quant q
        INNER JOIN stock_location l on l.id = q.location_id
        INNER JOIN stock_warehouse sw on sw.id = l.warehouse_id
        """

    def _query_search_qty_real_available_where_1(self):
        query = "WHERE l.usage = 'internal'"
        if self._fields.get("next_input_date"):
            query = "WHERE l.usage IN ('internal', 'transit')"
        company_id = self.env.context.get("force_sql_company", self.env.company.id)
        return f"""{query}
        AND l.company_id = {company_id}
        AND sw.consider_stock IS TRUE
        AND l.scrap_location IS FALSE
        AND (l.exclude_stock IS FALSE or l.exclude_stock IS NULL)
        """

    def _query_search_qty_real_available_groupby_1(self):
        return "GROUP BY q.product_id"

    def _query_search_qty_real_available_select_foo(self):
        return "SELECT foo2.product_id, sum(foo2.sum)"

    def _query_search_qty_real_available_groupby_foo(self):
        return "GROUP BY foo2.product_id"

    def _query_search_qty_real_available_select_2(self):
        return """
        SELECT m.product_id, l.usage,
        CASE WHEN l.usage = 'internal'
        THEN sum(product_uom_qty) * -1
        ELSE sum(product_uom_qty) END
        """

    def _query_search_qty_real_available_from_2(self):
        return """
        FROM stock_move m
        INNER JOIN stock_location l on l.id = m.location_id
        LEFT JOIN stock_warehouse sw on sw.id = l.warehouse_id
        INNER JOIN stock_location ld on ld.id = m.location_dest_id
        LEFT JOIN stock_warehouse swld on swld.id = ld.warehouse_id
        """

    def _query_search_qty_real_available_where_2(self):
        company_id = self.env.context.get("force_sql_company", self.env.company.id)
        query = f"""
        WHERE state NOT IN ('draft', 'cancel', 'done')
        AND m.company_id = {company_id}
        AND (
            (
                l.usage IN ('internal', 'view')
                AND ld.usage IN ('customer', 'production', 'samples', 'transit')
                AND sw.consider_stock IS TRUE AND l.scrap_location IS FALSE
                AND (l.exclude_stock IS FALSE OR l.exclude_stock IS NULL)
            )
            OR (
                l.usage = 'internal' AND ld.usage = 'internal'
                AND (
                    sw.consider_stock IS TRUE
                    AND (l.exclude_stock IS FALSE OR l.exclude_stock IS NULL)
                    AND (swld.consider_stock IS FALSE OR ld.exclude_stock IS TRUE)
                )
            )
            OR (
                l.usage IN ('customer', 'production', 'samples')
                AND ld.usage IN ('internal', 'view')
                AND m.company_id = 1
                AND swld.consider_stock IS TRUE
                AND l.scrap_location IS FALSE
                AND (ld.exclude_stock IS FALSE or ld.exclude_stock IS NULL)
            )
        """
        if self._fields.get("next_input_date"):
            query += """
            OR (l.usage = 'supplier' AND ld.usage IN ('transit', 'internal', 'view'))
            OR (l.usage = 'transit' AND ld.usage IN ('internal', 'view'))
            """
        query += ")"
        return query

    def _query_search_qty_real_available_groupby_2(self):
        return "GROUP BY l.usage, m.product_id"

    def _query_search_qty_real_available_union_subqueries(self):
        return [
            f"""
            {self._query_search_qty_real_available_select_1()}
            {self._query_search_qty_real_available_from_1()}
            {self._query_search_qty_real_available_where_1()}
            {self._query_search_qty_real_available_groupby_1()}
            """,
            f"""
            {self._query_search_qty_real_available_select_foo()}
            FROM (
                {self._query_search_qty_real_available_select_2()}
                {self._query_search_qty_real_available_from_2()}
                {self._query_search_qty_real_available_where_2()}
                {self._query_search_qty_real_available_groupby_2()}
            ) AS foo2
            {self._query_search_qty_real_available_groupby_foo()}
            """,
        ]

    def _query_search_qty_real_available(self):
        subqueries = self._query_search_qty_real_available_union_subqueries()
        return f"""
            {self._query_search_qty_real_available_select()}
            FROM (
                {" UNION ".join(subqueries)}
            ) AS foo
            {self._query_search_qty_real_available_groupby()}
            {self._query_search_qty_real_available_having()}
        """

    def _query_search_qty_production_select(self):
        return "SELECT product_id"

    def _query_search_qty_production_from(self):
        return """
            FROM stock_move m
            INNER JOIN stock_location l on l.id = m.location_id
        """

    def _query_search_qty_production_where(self):
        return """
            WHERE state NOT IN ('draft', 'cancel', 'done')
            AND l.usage IN ('production')
        """

    def _query_search_qty_production_groupby(self):
        return """
            GROUP BY product_id
        """

    def _query_search_qty_production_having(self):
        return """
            HAVING sum(product_uom_qty) %s %s
        """

    def _query_search_qty_production(self):
        return "{} {} {} {} {}".format(
            self._query_search_qty_production_select(),
            self._query_search_qty_production_from(),
            self._query_search_qty_production_where(),
            self._query_search_qty_production_groupby(),
            self._query_search_qty_production_having(),
        )

    # Search functions
    def _search_by_operator(self, field, operator, value):
        assert operator in ("<", ">", "=", "!=", "<=", ">="), "Invalid domain operator"
        assert isinstance(value, (float, int)), "Invalid domain right operand"
        res = []
        if getattr(self, "_query_search_%s" % field, False):
            query = getattr(self, "_query_search_%s" % field)()
            if operator == "=" and not value:
                operator = "!="
                query = self._get_not_in_query(query)
            elif operator in ["<=", ">="] and not value:
                self._cr.execute(query, (AsIs(operator[0]), value))
                res1 = [x[0] for x in self._cr.fetchall()]
                query = self._get_not_in_query(query)
                self._cr.execute(query, (AsIs("!="), value))
                res2 = [x[0] for x in self._cr.fetchall()]
                res = list(set(res1 + res2))
                return [("id", "in", res)]
            if self.env.context.get("locations_to_search", False):
                self._cr.execute(
                    query,
                    (
                        self.env.context["locations_to_search"],
                        AsIs(operator),
                        value or 0,
                    ),
                )
            else:
                self._cr.execute(query, (AsIs(operator), value or 0))
            res = [x[0] for x in self._cr.fetchall()]
        return [("id", "in", res)]

    def _get_not_in_query(self, query):
        return self._cr.mogrify(
            """SELECT pp.id from product_product as pp
                    INNER JOIN product_template as pt on pp.product_tmpl_id=pt.id
                    WHERE pp.id NOT IN(%s)
                    AND (pt.company_id = {} OR pt.company_id IS null)""".format(
                self.env.context.get("force_sql_company", self.env.company.id)
            ),
            [AsIs(query)],
        )

    def _search_qty_real(self, operator, value):
        return self._search_by_operator("qty_real", operator, value)

    def _search_qty_reserved(self, operator, value):
        return self._search_by_operator("qty_reserved", operator, value)

    def _search_qty_returned(self, operator, value):
        return self._search_by_operator("qty_returned", operator, value)

    def _search_qty_real_available(self, operator, value):
        return self._search_by_operator("qty_real_available", operator, value)

    def _search_qty_available(self, operator, value):
        return self._search_by_operator("qty_available_now", operator, value)

    def _search_qty_production(self, operator, value):
        return self._search_by_operator("qty_production", operator, value)

    qty_real = fields.Float(
        "Stock", compute="_compute_product_qtys", search="_search_qty_real"
    )
    qty_reserved = fields.Float(
        "Reservada", compute="_compute_product_qtys", search="_search_qty_reserved"
    )
    qty_returned = fields.Float(
        "Otras entradas previstas",
        compute="_compute_product_qtys",
        search="_search_qty_returned",
    )
    qty_real_available = fields.Float(
        "Disp. largo plazo",
        compute="_compute_product_qtys",
        search="_search_qty_real_available",
    )
    qty_available_now = fields.Float(
        string="Disp. inmediata",
        compute="_compute_product_qtys",
        search="_search_qty_available",
    )
    stock_location_ids = fields.Many2many(
        comodel_name="stock.location",
        relation="product_location_rel",
        column1="product_id",
        column2="location_id",
        string="Ubicaciones",
    )
    qty_production = fields.Float(
        "Cantidad fabricándose",
        compute="_compute_product_qtys",
        search="_search_qty_production",
    )

    def get_stock_from_date(self, date):
        self.ensure_one()
        assert isinstance(date, datetime), "Invalid date expected datetime object"
        date = date.replace(hour=23, minute=59, second=59)
        date = fields.Datetime.to_string(date)
        # RESERVADO
        _query_reserved = self._cr.mogrify(
            self._query_qty_reserved() + " AND date <= %s"
        )
        self._cr.execute(_query_reserved, (self.id, date))
        reserved = self._cr.fetchone()
        reserved = reserved and reserved[0] or 0
        # Devoluciones
        _query_returned = self._cr.mogrify(
            self._query_qty_returned() + " AND date <= %s"
        )
        self._cr.execute(_query_returned, [self.id, date])
        devoluciones = self._cr.fetchone()
        devoluciones = devoluciones and devoluciones[0] or 0
        qty_real = self.qty_real
        return {
            "date": date,
            "qty_real": qty_real,
            "qty_reserved": reserved,
            "qty_returning": devoluciones,
            "qty_real_available": qty_real + devoluciones - reserved,
        }

    def get_stock_from_location(self, location):
        pending_moves = self.env["stock.move"].search(
            [
                ("product_id", "=", self.id),
                ("state", "not in", ["draft", "cancel", "done"]),
                ("location_id.usage", "in", ["view", "internal"]),
                ("location_id", "child_of", location.id),
                ("location_dest_id.usage", "=", "customer"),
            ]
        )
        quants = self.env["stock.quant"].search(
            [
                ("product_id", "=", self.id),
                ("location_id.usage", "=", "internal"),
                ("location_id", "child_of", location.id),
            ]
        )
        qty_real = sum(q.quantity for q in quants)
        qty_reserved = sum(m.product_uom_qty for m in pending_moves)
        qty_real_available = qty_real - qty_reserved
        return {
            "qty_real": round(qty_real, 2),
            "qty_reserved": round(qty_reserved, 2),
            "qty_real_available": round(qty_real_available, 2),
        }

    def action_view_stock_moves(self):
        self.ensure_one()
        action = self.env.ref("stock.stock_move_action").read()[0]
        action["views"] = [(self.env.ref("stock.view_move_tree").id, "list")]
        action["context"] = self.env.context
        action["domain"] = [("product_id", "=", self.id)]
        return action

    def dummy_action(self):
        # Se usa para poder mostrar el disp. inmediata como un magic button
        return True
