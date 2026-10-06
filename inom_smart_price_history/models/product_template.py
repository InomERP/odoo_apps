# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ProductTemplate(models.Model):
    _inherit = "product.template"

    # Date range filters that drive the computed history lists (F-05 / F-06).
    invoice_history_date_from = fields.Date(string="Invoice From")
    invoice_history_date_to = fields.Date(string="Invoice To")
    bill_history_date_from = fields.Date(string="Bill From")
    bill_history_date_to = fields.Date(string="Bill To")

    invoice_history_line_ids = fields.Many2many(
        comodel_name="account.move.line",
        string="Customer Invoice History",
        compute="_compute_invoice_history_line_ids",
    )
    bill_history_line_ids = fields.Many2many(
        comodel_name="account.move.line",
        string="Vendor Bill History",
        compute="_compute_bill_history_line_ids",
    )
    price_change_log_ids = fields.One2many(
        comodel_name="inom.price.change.log",
        inverse_name="product_tmpl_id",
        string="Price Change Log",
        domain=lambda self: [("company_id", "in", self.env.companies.ids)],
    )

    def _get_history_move_lines(self, move_type, date_from, date_to):
        """Search the customer invoice or vendor bill lines for every variant
        of this template, honouring the active companies (multi-company support
        for F-06) and the optional date range.
        """
        self.ensure_one()
        variant_ids = self.product_variant_ids.ids
        if not variant_ids:
            return self.env["account.move.line"]
        domain = [
            ("product_id", "in", variant_ids),
            ("display_type", "=", "product"),
            ("move_id.move_type", "=", move_type),
            ("parent_state", "!=", "cancel"),
            ("company_id", "in", self.env.companies.ids),
        ]
        if date_from:
            domain.append(("date", ">=", date_from))
        if date_to:
            domain.append(("date", "<=", date_to))
        return self.env["account.move.line"].search(domain, order="date desc, id desc")

    @api.depends("product_variant_ids",
                 "invoice_history_date_from", "invoice_history_date_to")
    def _compute_invoice_history_line_ids(self):
        for template in self:
            template.invoice_history_line_ids = template._get_history_move_lines(
                "out_invoice",
                template.invoice_history_date_from,
                template.invoice_history_date_to,
            )

    @api.depends("product_variant_ids",
                 "bill_history_date_from", "bill_history_date_to")
    def _compute_bill_history_line_ids(self):
        for template in self:
            template.bill_history_line_ids = template._get_history_move_lines(
                "in_invoice",
                template.bill_history_date_from,
                template.bill_history_date_to,
            )
