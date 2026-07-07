# -*- coding: utf-8 -*-
from odoo import fields, models, tools


class InomSalesReportDetail(models.Model):
    """Detailed sales report (record level).

    A read-only SQL view over confirmed sale order lines exposing every
    dimension shown in the reference report screens (order, customer, product,
    category, company, country, state, city, sales team, salesperson,
    warehouse, order date, invoice status) plus quantity and amount measures.

    The same model powers several drill-down report screens; each screen simply
    opens this model with a different default group-by and view (list / graph /
    pivot). Only confirmed orders (state in 'sale' / 'done') are included.
    """

    _name = "inom.sales.report.detail"
    _description = "Sales Detail Report"
    _auto = False
    _order = "date_order desc"

    order_id = fields.Many2one("sale.order", string="Order", readonly=True)
    partner_id = fields.Many2one("res.partner", string="Customer", readonly=True)
    product_id = fields.Many2one("product.product", string="Product", readonly=True)
    categ_id = fields.Many2one("product.category", string="Product Category", readonly=True)
    company_id = fields.Many2one("res.company", string="Company", readonly=True)
    country_id = fields.Many2one("res.country", string="Country", readonly=True)
    state_id = fields.Many2one("res.country.state", string="State", readonly=True)
    city = fields.Char(string="City", readonly=True)
    team_id = fields.Many2one("crm.team", string="Sales Team", readonly=True)
    user_id = fields.Many2one("res.users", string="Salesperson", readonly=True)
    warehouse_id = fields.Many2one("stock.warehouse", string="Warehouse", readonly=True)
    date_order = fields.Datetime(string="Order Date", readonly=True)
    invoice_status = fields.Selection(
        selection=[
            ("upselling", "Upselling Opportunity"),
            ("invoiced", "Fully Invoiced"),
            ("to invoice", "To Invoice"),
            ("no", "Nothing to Invoice"),
        ],
        string="Invoice Status",
        readonly=True,
    )
    quantity = fields.Float(string="Quantity", readonly=True)
    amount = fields.Float(string="Total", readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(f"""
            CREATE VIEW {self._table} AS (
                SELECT
                    sol.id AS id,
                    sol.order_id AS order_id,
                    so.partner_id AS partner_id,
                    sol.product_id AS product_id,
                    pt.categ_id AS categ_id,
                    so.company_id AS company_id,
                    rp.country_id AS country_id,
                    rp.state_id AS state_id,
                    rp.city AS city,
                    so.team_id AS team_id,
                    so.user_id AS user_id,
                    so.warehouse_id AS warehouse_id,
                    so.date_order AS date_order,
                    so.invoice_status AS invoice_status,
                    sol.product_uom_qty AS quantity,
                    sol.price_subtotal AS amount
                FROM sale_order_line sol
                JOIN sale_order so ON so.id = sol.order_id
                JOIN res_partner rp ON rp.id = so.partner_id
                LEFT JOIN product_product pp ON pp.id = sol.product_id
                LEFT JOIN product_template pt ON pt.id = pp.product_tmpl_id
                WHERE so.state IN ('sale', 'done')
                  AND sol.product_id IS NOT NULL
            )
        """)
