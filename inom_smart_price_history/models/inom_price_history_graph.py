# -*- coding: utf-8 -*-
from odoo import models, fields, tools


class InomPriceHistoryGraph(models.Model):
    _name = "inom.price.history.graph"
    _description = "Product Price History Graph"
    _auto = False
    _order = "change_date asc"

    product_id = fields.Many2one(
        comodel_name="product.product",
        string="Product",
        readonly=True,
    )
    product_tmpl_id = fields.Many2one(
        comodel_name="product.template",
        string="Product Template",
        readonly=True,
    )
    source = fields.Selection(
        selection=[
            ("invoice", "Customer Invoice"),
            ("bill", "Vendor Bill"),
            ("purchase", "Purchase Order"),
            ("cost", "Cost Update"),
            ("sale", "Sale Order"),
        ],
        string="Source",
        readonly=True,
    )
    old_price = fields.Float(string="Old Price", readonly=True)
    new_price = fields.Float(
        string="New Price", readonly=True, aggregator="avg"
    )
    change_date = fields.Datetime(string="Date", readonly=True)
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        readonly=True,
    )

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                SELECT
                    l.id AS id,
                    l.product_id AS product_id,
                    l.product_tmpl_id AS product_tmpl_id,
                    l.source AS source,
                    l.old_price AS old_price,
                    l.new_price AS new_price,
                    l.change_date AS change_date,
                    l.company_id AS company_id
                FROM inom_price_change_log l

                UNION ALL

                SELECT
                    -1 * s.id AS id,
                    s.product_id AS product_id,
                    p.product_tmpl_id AS product_tmpl_id,
                    'sale' AS source,
                    s.old_price AS old_price,
                    s.new_price AS new_price,
                    s.change_date AS change_date,
                    s.company_id AS company_id
                FROM inom_sale_price_log s
                JOIN product_product p ON p.id = s.product_id
            )
        """ % self._table)
