# -*- coding: utf-8 -*-
from odoo import api, models


class InomBranchDashboard(models.AbstractModel):
    _name = "inom.branch.dashboard"
    _description = "Branch Dashboard Data Provider"

    @api.model
    def get_dashboard_data(self):
        """Return branch wise KPIs consumed by the OWL dashboard."""
        move_model = self.env["account.move"]
        currency = self.env.company.currency_id

        def _read(domain, field):
            groups = move_model.read_group(
                domain, ["%s:sum" % field], ["inom_branch_id"],
            )
            data = {}
            for grp in groups:
                branch = grp.get("inom_branch_id")
                key = branch[0] if branch else 0
                data[key] = {
                    "amount": grp.get(field, 0.0) or 0.0,
                    "count": grp.get("__count", 0) or grp.get(
                        "inom_branch_id_count", 0),
                }
            return data

        def _dom(move_type):
            return [("move_type", "=", move_type), ("state", "=", "posted")]

        sales = _read(_dom("out_invoice"), "amount_total")
        refunds = _read(_dom("out_refund"), "amount_total")
        bills = _read(_dom("in_invoice"), "amount_total")
        vbills_refund = _read(_dom("in_refund"), "amount_total")
        receivable = _read(
            [("move_type", "=", "out_invoice"), ("state", "=", "posted"),
             ("payment_state", "in", ("not_paid", "partial"))],
            "amount_residual",
        )

        branches = self.env["inom.branch"].search([
            ("company_id", "in", self.env.companies.ids),
        ])

        rows = []
        total_sales = total_purchase = total_receivable = 0.0
        for branch in branches:
            s = sales.get(branch.id, {}).get("amount", 0.0)
            sr = refunds.get(branch.id, {}).get("amount", 0.0)
            p = bills.get(branch.id, {}).get("amount", 0.0)
            pr = vbills_refund.get(branch.id, {}).get("amount", 0.0)
            due = receivable.get(branch.id, {}).get("amount", 0.0)
            net_sales = s - sr
            net_purchase = p - pr
            total_sales += net_sales
            total_purchase += net_purchase
            total_receivable += due
            rows.append({
                "id": branch.id,
                "name": branch.name or branch.display_name,
                "code": branch.code or "",
                "color": branch.color or 0,
                "sales": net_sales,
                "purchase": net_purchase,
                "net": net_sales - net_purchase,
                "receivable": due,
                "invoice_count": sales.get(branch.id, {}).get("count", 0),
                "bill_count": bills.get(branch.id, {}).get("count", 0),
            })

        # ---- Invoice summary (customer invoices) ----
        inv_groups = move_model.read_group(
            [("move_type", "=", "out_invoice"), ("state", "=", "posted")],
            ["amount_total:sum", "amount_residual:sum"], [],
        )
        total_invoiced = 0.0
        outstanding_total = 0.0
        if inv_groups:
            total_invoiced = inv_groups[0].get("amount_total", 0.0) or 0.0
            outstanding_total = inv_groups[0].get("amount_residual", 0.0) or 0.0
        collected = total_invoiced - outstanding_total
        paid_count = move_model.search_count([
            ("move_type", "=", "out_invoice"), ("state", "=", "posted"),
            ("payment_state", "in", ("paid", "in_payment", "reversed")),
        ])
        unpaid_count = move_model.search_count([
            ("move_type", "=", "out_invoice"), ("state", "=", "posted"),
            ("payment_state", "in", ("not_paid", "partial")),
        ])
        invoice_summary = {
            "total_invoiced": total_invoiced,
            "collected": collected,
            "outstanding": outstanding_total,
            "paid_count": paid_count,
            "unpaid_count": unpaid_count,
        }

        # ---- Vendor / payables summary (vendor bills) ----
        bill_groups = move_model.read_group(
            [("move_type", "=", "in_invoice"), ("state", "=", "posted")],
            ["amount_total:sum", "amount_residual:sum"], [],
        )
        total_billed = 0.0
        payable_total = 0.0
        if bill_groups:
            total_billed = bill_groups[0].get("amount_total", 0.0) or 0.0
            payable_total = bill_groups[0].get("amount_residual", 0.0) or 0.0
        bill_paid = total_billed - payable_total
        bill_paid_count = move_model.search_count([
            ("move_type", "=", "in_invoice"), ("state", "=", "posted"),
            ("payment_state", "in", ("paid", "in_payment", "reversed")),
        ])
        bill_due_count = move_model.search_count([
            ("move_type", "=", "in_invoice"), ("state", "=", "posted"),
            ("payment_state", "in", ("not_paid", "partial")),
        ])
        vendor_summary = {
            "total_billed": total_billed,
            "paid": bill_paid,
            "payable": payable_total,
            "paid_count": bill_paid_count,
            "due_count": bill_due_count,
        }

        rows.sort(key=lambda r: r["sales"], reverse=True)

        return {
            "currency_symbol": currency.symbol or "",
            "currency_position": currency.position or "before",
            "total_sales": total_sales,
            "total_purchase": total_purchase,
            "total_receivable": total_receivable,
            "total_branches": len(branches),
            "invoice_summary": invoice_summary,
            "vendor_summary": vendor_summary,
            "branches": rows,
        }
