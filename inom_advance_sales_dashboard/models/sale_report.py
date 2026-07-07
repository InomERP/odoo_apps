# -*- coding: utf-8 -*-
from odoo import fields, models, tools


# Revenue basis (kept consistent with the dashboard, per SRS section 7):
#   * Product / category reports (R-01, R-02, R-03) use line price_subtotal.
#   * Customer / order reports (R-04, R-05) use order amount_total.
# Only confirmed orders (state in 'sale' / 'done') are considered.


class InomSalesReportMonthlyGrowth(models.Model):
    """R-01 - Monthly Sales Growth Report.

    One row per calendar month per dimension tuple
    (product, customer, salesperson, sales team) with the month revenue, the
    previous-month revenue for the same tuple and the month-over-month growth
    percentage. Users can group the list by any dimension.
    """

    _name = "inom.sales.report.monthly.growth"
    _description = "Monthly Sales Growth Report"
    _auto = False
    _order = "month_date desc"

    month_date = fields.Date(string="Month", readonly=True)
    product_id = fields.Many2one("product.product", string="Product", readonly=True)
    categ_id = fields.Many2one("product.category", string="Product Category", readonly=True)
    partner_id = fields.Many2one("res.partner", string="Customer", readonly=True)
    user_id = fields.Many2one("res.users", string="Salesperson", readonly=True)
    team_id = fields.Many2one("crm.team", string="Sales Team", readonly=True)
    revenue = fields.Float(string="Revenue", readonly=True)
    previous_revenue = fields.Float(string="Previous-Month Revenue", readonly=True)
    growth_pct = fields.Float(string="Growth %", readonly=True, group_operator="avg")

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(f"""
            CREATE VIEW {self._table} AS (
                SELECT
                    row_number() OVER () AS id,
                    base.month_date,
                    base.product_id,
                    base.categ_id,
                    base.partner_id,
                    base.user_id,
                    base.team_id,
                    base.revenue,
                    base.previous_revenue,
                    CASE
                        WHEN base.previous_revenue IS NULL OR base.previous_revenue = 0 THEN 0
                        ELSE round(
                            (base.revenue - base.previous_revenue) / base.previous_revenue * 100, 2
                        )
                    END AS growth_pct
                FROM (
                    SELECT
                        g.month_date,
                        g.product_id,
                        g.categ_id,
                        g.partner_id,
                        g.user_id,
                        g.team_id,
                        g.revenue,
                        LAG(g.revenue) OVER (
                            PARTITION BY g.product_id, g.partner_id, g.user_id, g.team_id
                            ORDER BY g.month_date
                        ) AS previous_revenue
                    FROM (
                        SELECT
                            date_trunc('month', so.date_order)::date AS month_date,
                            sol.product_id AS product_id,
                            pt.categ_id AS categ_id,
                            so.partner_id AS partner_id,
                            so.user_id AS user_id,
                            so.team_id AS team_id,
                            SUM(sol.price_subtotal) AS revenue
                        FROM sale_order_line sol
                        JOIN sale_order so ON so.id = sol.order_id
                        JOIN product_product pp ON pp.id = sol.product_id
                        JOIN product_template pt ON pt.id = pp.product_tmpl_id
                        WHERE so.state IN ('sale', 'done')
                          AND sol.product_id IS NOT NULL
                        GROUP BY 1, 2, 3, 4, 5, 6
                    ) g
                ) base
            )
        """)


class InomSalesReportCategory(models.Model):
    """R-02 - Sales Revenue Breakdown by Product Category."""

    _name = "inom.sales.report.category"
    _description = "Sales Revenue Breakdown by Product Category"
    _auto = False
    _order = "revenue desc"

    categ_id = fields.Many2one("product.category", string="Product Category", readonly=True)
    revenue = fields.Float(string="Revenue", readonly=True)
    revenue_pct = fields.Float(string="% of Total Revenue", readonly=True, group_operator="avg")

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(f"""
            CREATE VIEW {self._table} AS (
                SELECT
                    row_number() OVER () AS id,
                    c.categ_id,
                    c.revenue,
                    CASE
                        WHEN t.grand_total = 0 THEN 0
                        ELSE round(c.revenue / t.grand_total * 100, 2)
                    END AS revenue_pct
                FROM (
                    SELECT
                        pt.categ_id AS categ_id,
                        SUM(sol.price_subtotal) AS revenue
                    FROM sale_order_line sol
                    JOIN sale_order so ON so.id = sol.order_id
                    JOIN product_product pp ON pp.id = sol.product_id
                    JOIN product_template pt ON pt.id = pp.product_tmpl_id
                    WHERE so.state IN ('sale', 'done')
                      AND sol.product_id IS NOT NULL
                    GROUP BY pt.categ_id
                ) c
                CROSS JOIN (
                    SELECT SUM(sol.price_subtotal) AS grand_total
                    FROM sale_order_line sol
                    JOIN sale_order so ON so.id = sol.order_id
                    WHERE so.state IN ('sale', 'done')
                      AND sol.product_id IS NOT NULL
                ) t
            )
        """)


class InomSalesReportTopProducts(models.Model):
    """R-03 - Top 5 Highest-Selling Products Report."""

    _name = "inom.sales.report.top.products"
    _description = "Top 5 Highest-Selling Products Report"
    _auto = False
    _order = "rank_no"

    rank_no = fields.Integer(string="Rank", readonly=True)
    product_id = fields.Many2one("product.product", string="Product", readonly=True)
    quantity = fields.Float(string="Quantity Sold", readonly=True)
    revenue = fields.Float(string="Revenue", readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(f"""
            CREATE VIEW {self._table} AS (
                SELECT
                    t.id,
                    t.id AS rank_no,
                    t.product_id,
                    t.quantity,
                    t.revenue
                FROM (
                    SELECT
                        row_number() OVER (
                            ORDER BY SUM(sol.product_uom_qty) DESC, SUM(sol.price_subtotal) DESC
                        ) AS id,
                        sol.product_id AS product_id,
                        SUM(sol.product_uom_qty) AS quantity,
                        SUM(sol.price_subtotal) AS revenue
                    FROM sale_order_line sol
                    JOIN sale_order so ON so.id = sol.order_id
                    WHERE so.state IN ('sale', 'done')
                      AND sol.product_id IS NOT NULL
                    GROUP BY sol.product_id
                ) t
                WHERE t.id <= 5
            )
        """)


class InomSalesReportClv(models.Model):
    """R-04 - Customer Lifetime Value Analysis."""

    _name = "inom.sales.report.clv"
    _description = "Customer Lifetime Value Analysis"
    _auto = False
    _order = "lifetime_revenue desc"

    partner_id = fields.Many2one("res.partner", string="Customer", readonly=True)
    first_order_date = fields.Datetime(string="First Order Date", readonly=True)
    total_orders = fields.Integer(string="Total Orders", readonly=True)
    lifetime_revenue = fields.Float(string="Lifetime Revenue", readonly=True)
    avg_order_value = fields.Float(string="Average Order Value", readonly=True, group_operator="avg")

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(f"""
            CREATE VIEW {self._table} AS (
                SELECT
                    row_number() OVER () AS id,
                    so.partner_id,
                    MIN(so.date_order) AS first_order_date,
                    COUNT(so.id) AS total_orders,
                    SUM(so.amount_total) AS lifetime_revenue,
                    CASE
                        WHEN COUNT(so.id) = 0 THEN 0
                        ELSE round(SUM(so.amount_total) / COUNT(so.id), 2)
                    END AS avg_order_value
                FROM sale_order so
                WHERE so.state IN ('sale', 'done')
                  AND so.partner_id IS NOT NULL
                GROUP BY so.partner_id
            )
        """)


class InomSalesReportNewRepeat(models.Model):
    """R-05 - New vs Repeat Customer Performance Report.

    Orders are classified at order level: a customer's first-ever confirmed
    order is a "New" order; every subsequent confirmed order is a "Repeat"
    order. Figures are aggregated per segment.
    """

    _name = "inom.sales.report.new.repeat"
    _description = "New vs Repeat Customer Performance Report"
    _auto = False
    _order = "segment"

    segment = fields.Char(string="Segment", readonly=True)
    customers = fields.Integer(string="Customers", readonly=True)
    orders = fields.Integer(string="Orders", readonly=True)
    revenue = fields.Float(string="Revenue", readonly=True)
    avg_order_value = fields.Float(string="Average Order Value", readonly=True, group_operator="avg")

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(f"""
            CREATE VIEW {self._table} AS (
                WITH ranked AS (
                    SELECT
                        so.id,
                        so.partner_id,
                        so.amount_total,
                        row_number() OVER (
                            PARTITION BY so.partner_id ORDER BY so.date_order, so.id
                        ) AS seq
                    FROM sale_order so
                    WHERE so.state IN ('sale', 'done')
                      AND so.partner_id IS NOT NULL
                )
                SELECT
                    row_number() OVER () AS id,
                    seg.segment,
                    seg.customers,
                    seg.orders,
                    seg.revenue,
                    CASE
                        WHEN seg.orders = 0 THEN 0
                        ELSE round(seg.revenue / seg.orders, 2)
                    END AS avg_order_value
                FROM (
                    SELECT
                        'New' AS segment,
                        COUNT(DISTINCT partner_id) AS customers,
                        COUNT(*) AS orders,
                        SUM(amount_total) AS revenue
                    FROM ranked
                    WHERE seq = 1
                    UNION ALL
                    SELECT
                        'Repeat' AS segment,
                        COUNT(DISTINCT partner_id) AS customers,
                        COUNT(*) AS orders,
                        SUM(amount_total) AS revenue
                    FROM ranked
                    WHERE seq > 1
                ) seg
            )
        """)
