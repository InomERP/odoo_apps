# -*- coding: utf-8 -*-
from odoo import models, api


class ProductPriceHistoryReport(models.AbstractModel):
    _name = "report.inom_smart_price_history.price_history_tmpl"
    _description = "Product Price History PDF Report"

    @api.model
    def _get_report_values(self, docids, data=None):
        wizard_id = (data or {}).get("wizard_id")
        wizard = self.env["product.price.history.report.wizard"].browse(wizard_id)
        if not wizard.exists():
            wizard = self.env["product.price.history.report.wizard"].browse(docids)
        lines = wizard._get_history_lines() if wizard.exists() else []
        return {
            "doc_ids": docids,
            "doc_model": "product.price.history.report.wizard",
            "docs": wizard,
            "lines": lines,
            "company": self.env.company,
        }
