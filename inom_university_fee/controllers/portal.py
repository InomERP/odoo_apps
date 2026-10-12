# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal


class UniversityFeePortal(CustomerPortal):
    """Student/parent self-service fee area."""

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if "fee_invoice_count" in counters:
            partner = request.env.user.partner_id
            values["fee_invoice_count"] = (
                request.env["univ.fee.invoice"]
                .sudo()
                .search_count([("partner_id", "=", partner.id)])
            )
        return values

    def _get_fee_invoices(self):
        partner = request.env.user.partner_id
        return (
            request.env["univ.fee.invoice"]
            .sudo()
            .search(
                [("partner_id", "=", partner.id), ("move_state", "=", "posted")],
                order="due_date asc, id desc",
            )
        )

    @http.route(["/my/fees"], type="http", auth="user", website=True)
    def portal_my_fees(self, **kw):
        invoices = self._get_fee_invoices()
        totals = {
            "invoiced": sum(invoices.mapped("amount_total")),
            "paid": sum(invoices.mapped("amount_paid")),
            "outstanding": sum(invoices.mapped("amount_residual")),
        }
        # Native invoice portal URLs (view + Pay Now). The account/account_payment
        # portal handles online payment, receipt PDF and access tokens, so fees
        # reuse the standard audited flow rather than duplicating it.
        invoice_urls = {}
        for inv in invoices:
            if inv.move_id:
                invoice_urls[inv.id] = inv.move_id.get_portal_url()
        FeeInvoice = request.env["univ.fee.invoice"]
        values = {
            "page_name": "fees",
            "fee_invoices": invoices,
            "totals": totals,
            "currency": request.env.company.currency_id,
            "state_labels": dict(FeeInvoice._fields["state"].selection),
            "invoice_urls": invoice_urls,
        }
        return request.render("inom_university_fee.portal_my_fees", values)
