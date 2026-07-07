# -*- coding: utf-8 -*-
from odoo import fields, models


class InomSalesReportWizard(models.TransientModel):
    """Sales report filter wizard.

    Mirrors the reference module's filter dialog: the user chooses a date range
    and optional product categories, products, companies and warehouses, then
    opens the detailed report either as data (list) or as a graph.
    """

    _name = "inom.sales.report.wizard"
    _description = "Sales Report Filter"

    date_from = fields.Date(string="Start Date")
    date_to = fields.Date(string="End Date")
    category_ids = fields.Many2many("product.category", string="Product Categories")
    product_ids = fields.Many2many("product.product", string="Products")
    company_ids = fields.Many2many("res.company", string="Companies")
    warehouse_ids = fields.Many2many("stock.warehouse", string="Warehouses")

    def _build_domain(self):
        self.ensure_one()
        domain = []
        if self.date_from:
            domain.append(("date_order", ">=", self.date_from))
        if self.date_to:
            domain.append(("date_order", "<=", self.date_to))
        if self.category_ids:
            domain.append(("categ_id", "in", self.category_ids.ids))
        if self.product_ids:
            domain.append(("product_id", "in", self.product_ids.ids))
        if self.company_ids:
            domain.append(("company_id", "in", self.company_ids.ids))
        if self.warehouse_ids:
            domain.append(("warehouse_id", "in", self.warehouse_ids.ids))
        return domain

    def _action(self, view_mode, name):
        return {
            "type": "ir.actions.act_window",
            "name": name,
            "res_model": "inom.sales.report.detail",
            "view_mode": view_mode,
            "domain": self._build_domain(),
            "context": {"group_by": ["categ_id"]},
            "target": "current",
        }

    def action_view_data(self):
        return self._action("tree,graph,pivot", "Sales Report - Data")

    def action_view_graph(self):
        return self._action("graph,pivot,tree", "Sales Report - Graph")
