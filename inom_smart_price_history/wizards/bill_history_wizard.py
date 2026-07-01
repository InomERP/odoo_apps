# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class BillHistoryWizard(models.TransientModel):
    _name = "bill.history.wizard"
    _description = "Vendor Bill Price History"

    product_id = fields.Many2one(
        comodel_name="product.product",
        string="Product",
        readonly=True,
    )
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Vendor",
        readonly=True,
    )
    line_ids = fields.One2many(
        comodel_name="bill.history.wizard.line",
        inverse_name="wizard_id",
        string="History Lines",
        readonly=True,
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        product_id = res.get("product_id") or self.env.context.get("default_product_id")
        partner_id = res.get("partner_id") or self.env.context.get("default_partner_id")
        if product_id and partner_id and "line_ids" in fields_list:
            product = self.env["product.product"].browse(product_id)
            partner = self.env["res.partner"].browse(partner_id)
            res["line_ids"] = self._prepare_history_lines(product, partner)
        return res

    def _prepare_history_lines(self, product, partner):
        """Build (0, 0, vals) commands for every vendor bill line that matches
        the given product and the commercial partner of the vendor.

        The read is performed with sudo() because a purchase user may not hold
        direct accounting access rights, yet must be able to review the price
        history for a product they are already purchasing. The query is strictly
        scoped to a single product, a single commercial partner and only the
        companies currently active for the user, so no unrelated accounting
        data can be exposed through this wizard.
        """
        commercial_partner = partner.commercial_partner_id
        domain = [
            ("product_id", "=", product.id),
            ("display_type", "=", "product"),
            ("move_id.move_type", "=", "in_invoice"),
            ("move_id.commercial_partner_id", "=", commercial_partner.id),
            ("company_id", "in", self.env.companies.ids),
        ]
        move_lines = self.env["account.move.line"].sudo().search(domain)
        # Sort by the bill date in descending order (newest first).
        move_lines = move_lines.sorted(
            key=lambda line: (
                line.move_id.invoice_date or line.date or fields.Date.today()
            ),
            reverse=True,
        )
        commands = []
        for line in move_lines:
            commands.append((0, 0, {
                "move_id": line.move_id.id,
                "invoice_date": line.move_id.invoice_date or line.date,
                "quantity": line.quantity,
                "price_unit": line.price_unit,
                "price_subtotal": line.price_subtotal,
                "state": line.parent_state,
                "currency_id": line.currency_id.id,
            }))
        return commands


class BillHistoryWizardLine(models.TransientModel):
    _name = "bill.history.wizard.line"
    _description = "Vendor Bill Price History Line"
    _order = "invoice_date desc, id desc"

    wizard_id = fields.Many2one(
        comodel_name="bill.history.wizard",
        string="Wizard",
        ondelete="cascade",
    )
    move_id = fields.Many2one(
        comodel_name="account.move",
        string="Bill",
        readonly=True,
    )
    invoice_date = fields.Date(string="Date", readonly=True)
    quantity = fields.Float(string="Quantity", readonly=True)
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        string="Currency",
        readonly=True,
    )
    price_unit = fields.Monetary(
        string="Unit Price",
        currency_field="currency_id",
        readonly=True,
    )
    price_subtotal = fields.Monetary(
        string="Subtotal",
        currency_field="currency_id",
        readonly=True,
    )
    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("posted", "Posted"),
            ("cancel", "Cancelled"),
        ],
        string="Bill State",
        readonly=True,
    )
