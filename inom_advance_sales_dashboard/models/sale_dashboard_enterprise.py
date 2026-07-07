# -*- coding: utf-8 -*-
from odoo import api, models


class SaleDashboardEnterprise(models.AbstractModel):
    """Enterprise analytics for the Advanced Sales Dashboard.

    This inherits the existing ``sale.dashboard`` abstract model and only ADDS
    new aggregation methods. It does not modify or override any existing method,
    calculation, report, model, security rule or database structure.

    All reads are grouped ORM reads (``read_group``) to avoid N+1 queries and to
    stay fast on large datasets. Multi-company visibility and user access rights
    are enforced automatically by Odoo's record rules on the underlying models.
    The optional ``filters`` dict (salesperson/team/partner/company/category) is
    applied additively through the shared ``_get_filter_leaves`` helper.
    """

    _inherit = "sale.dashboard"

    # ------------------------------------------------------------------
    # Shared domain helpers (period + advanced filters, state-agnostic)
    # ------------------------------------------------------------------
    def _ent_period_leaves(self, date_from, date_to, field="date_order"):
        leaves = []
        if date_from:
            leaves.append((field, ">=", date_from))
        if date_to:
            leaves.append((field, "<=", date_to))
        return leaves

    def _ent_order_domain(self, date_from, date_to, extra=None):
        domain = self._ent_period_leaves(date_from, date_to)
        domain += self._get_filter_leaves(prefix="")
        if extra:
            domain += extra
        return domain

    def _ent_move_leaves(self):
        """Map the advanced filters onto account.move fields."""
        filters = self.env.context.get("inom_dashboard_filters") or {}
        leaves = []
        if filters.get("salesperson_ids"):
            leaves.append(("invoice_user_id", "in", filters["salesperson_ids"]))
        if filters.get("team_ids"):
            leaves.append(("team_id", "in", filters["team_ids"]))
        if filters.get("partner_ids"):
            leaves.append(("partner_id", "in", filters["partner_ids"]))
        if filters.get("company_ids"):
            leaves.append(("company_id", "in", filters["company_ids"]))
        return leaves

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------
    @api.model
    def get_enterprise_data(self, date_from=None, date_to=None, filters=None):
        if filters:
            self = self.with_context(inom_dashboard_filters=filters)
        currency = self.env.company.currency_id
        return {
            "currency": {"id": currency.id, "symbol": currency.symbol},
            "funnel": self._ent_get_funnel(date_from, date_to),
            "leaderboard": self._ent_get_leaderboard(date_from, date_to),
            "products": self._ent_get_products(date_from, date_to),
            "target_achievement": self._ent_get_target_achievement(date_from, date_to),
        }

    # ------------------------------------------------------------------
    # 1) Sales Funnel
    # ------------------------------------------------------------------
    def _ent_get_funnel(self, date_from, date_to):
        SaleOrder = self.env["sale.order"]

        def single(extra):
            groups = SaleOrder.read_group(
                self._ent_order_domain(date_from, date_to, extra),
                ["amount_total:sum"], [],
            )
            if groups:
                return groups[0].get("__count") or 0, round(groups[0].get("amount_total") or 0.0, 2)
            return 0, 0.0

        quot_count, quot_amount = single([("state", "!=", "cancel")])
        so_count, so_amount = single([("state", "in", self._CONFIRMED_STATES)])

        # Delivered: confirmed orders that have at least one done outgoing picking.
        delivered_count, delivered_amount = 0, 0.0
        picking_groups = self.env["stock.picking"].read_group(
            [("picking_type_id.code", "=", "outgoing"), ("state", "=", "done"), ("sale_id", "!=", False)],
            ["sale_id"], ["sale_id"],
        )
        delivered_ids = [g["sale_id"][0] for g in picking_groups if g.get("sale_id")]
        if delivered_ids:
            delivered_count, delivered_amount = single([
                ("state", "in", self._CONFIRMED_STATES), ("id", "in", delivered_ids),
            ])

        inv_count, inv_amount = single([
            ("state", "in", self._CONFIRMED_STATES), ("invoice_status", "=", "invoiced"),
        ])

        # Paid: posted customer invoices that are paid within the window.
        move_domain = [
            ("move_type", "=", "out_invoice"),
            ("state", "=", "posted"),
            ("payment_state", "in", ["paid", "in_payment"]),
        ]
        move_domain += self._ent_period_leaves(date_from, date_to, field="invoice_date")
        move_domain += self._ent_move_leaves()
        paid_groups = self.env["account.move"].read_group(move_domain, ["amount_total:sum"], [])
        paid_count = (paid_groups[0].get("__count") or 0) if paid_groups else 0
        paid_amount = round((paid_groups[0].get("amount_total") or 0.0), 2) if paid_groups else 0.0

        raw = [
            ("quotation", "Quotation", quot_count, quot_amount),
            ("sale_order", "Sales Order", so_count, so_amount),
            ("delivery", "Delivery", delivered_count, delivered_amount),
            ("invoice", "Invoice", inv_count, inv_amount),
            ("payment", "Payment", paid_count, paid_amount),
        ]
        base = quot_count or 0
        stages = []
        prev_count = None
        for key, label, count, amount in raw:
            conversion = round(count / base * 100, 2) if base else 0.0
            dropoff = 0.0
            if prev_count:
                dropoff = round((prev_count - count) / prev_count * 100, 2)
            stages.append({
                "key": key, "label": label, "count": count, "amount": amount,
                "conversion": conversion, "dropoff": max(dropoff, 0.0),
            })
            prev_count = count
        return stages

    # ------------------------------------------------------------------
    # 2) Salesperson Performance Leaderboard
    # ------------------------------------------------------------------
    def _ent_get_leaderboard(self, date_from, date_to):
        SaleOrder = self.env["sale.order"]

        confirmed = SaleOrder.read_group(
            self._ent_order_domain(date_from, date_to, [("state", "in", self._CONFIRMED_STATES)]),
            ["amount_total:sum"], ["user_id"],
        )
        total = SaleOrder.read_group(
            self._ent_order_domain(date_from, date_to, [("state", "!=", "cancel")]),
            [], ["user_id"],
        )
        total_by_user = {g["user_id"][0]: (g.get("__count") or 0) for g in total if g.get("user_id")}

        # Teams each salesperson sold in -> attribute team targets (indicator).
        team_target = self._get_targets_by_team(date_from, date_to)
        user_team = SaleOrder.read_group(
            self._ent_order_domain(date_from, date_to, [("state", "in", self._CONFIRMED_STATES)]),
            [], ["user_id", "team_id"], lazy=False,
        )
        target_by_user = {}
        for g in user_team:
            if not g.get("user_id") or not g.get("team_id"):
                continue
            uid = g["user_id"][0]
            target_by_user.setdefault(uid, 0.0)
            target_by_user[uid] += team_target.get(g["team_id"][0], 0.0)

        rows = []
        for g in confirmed:
            if not g.get("user_id"):
                continue
            uid = g["user_id"][0]
            revenue = round(g.get("amount_total") or 0.0, 2)
            orders = g.get("__count") or 0
            total_q = total_by_user.get(uid, orders)
            target = round(target_by_user.get(uid, 0.0), 2)
            achievement = round(revenue / target * 100, 2) if target else 0.0
            rows.append({
                "user_id": uid,
                "salesperson": g["user_id"][1],
                "revenue": revenue,
                "orders": orders,
                "avg_order_value": round(revenue / orders, 2) if orders else 0.0,
                "win_rate": round(orders / total_q * 100, 2) if total_q else 0.0,
                "target": target,
                "has_target": bool(target),
                "achievement": achievement,
            })
        rows.sort(key=lambda r: r["revenue"], reverse=True)
        for index, row in enumerate(rows):
            row["rank"] = index + 1
        return rows

    # ------------------------------------------------------------------
    # 3) Product Performance Analytics
    # ------------------------------------------------------------------
    def _ent_get_products(self, date_from, date_to):
        Line = self.env["sale.order.line"]
        domain = [("order_id.state", "in", self._CONFIRMED_STATES), ("product_id", "!=", False)]
        domain += self._ent_period_leaves(date_from, date_to, field="order_id.date_order")
        domain += self._get_filter_leaves(prefix="order_id.")

        groups = Line.read_group(
            domain, ["product_uom_qty:sum", "price_subtotal:sum"], ["product_id"],
        )
        product_ids = [g["product_id"][0] for g in groups if g.get("product_id")]
        cost_map = {}
        if product_ids:
            for product in self.env["product.product"].browse(product_ids):
                cost_map[product.id] = product.standard_price or 0.0

        items = []
        for g in groups:
            if not g.get("product_id"):
                continue
            pid = g["product_id"][0]
            qty = round(g.get("product_uom_qty") or 0.0, 2)
            revenue = round(g.get("price_subtotal") or 0.0, 2)
            frequency = g.get("__count") or 0
            margin = round(revenue - cost_map.get(pid, 0.0) * qty, 2)
            items.append({
                "product_id": pid, "product_name": g["product_id"][1],
                "quantity": qty, "revenue": revenue, "margin": margin, "frequency": frequency,
            })

        def top(field, reverse=True, limit=5):
            return sorted(items, key=lambda x: x[field], reverse=reverse)[:limit]

        return {
            "top_selling": top("quantity"),
            "highest_revenue": top("revenue"),
            "highest_margin": top("margin"),
            "least_selling": top("quantity", reverse=False),
            "fast_moving": top("frequency"),
            "slow_moving": top("frequency", reverse=False),
        }

    # ------------------------------------------------------------------
    # 4) Target vs Achievement (monthly)
    # ------------------------------------------------------------------
    def _ent_get_target_achievement(self, date_from, date_to):
        SaleOrder = self.env["sale.order"]
        # Overall actual (confirmed revenue) and overall target.
        overall = SaleOrder.read_group(
            self._ent_order_domain(date_from, date_to, [("state", "in", self._CONFIRMED_STATES)]),
            ["amount_total:sum"], [],
        )
        actual = round((overall[0].get("amount_total") or 0.0), 2) if overall else 0.0
        target = round(sum(self._get_targets_by_team(date_from, date_to).values()), 2)
        achievement = round(actual / target * 100, 2) if target else 0.0
        remaining = round(max(target - actual, 0.0), 2)

        # Monthly actual, with an evenly pro-rated monthly target indicator.
        monthly_groups = SaleOrder.with_context(
            tz=self._get_dashboard_timezone()
        ).read_group(
            self._ent_order_domain(date_from, date_to, [("state", "in", self._CONFIRMED_STATES)]),
            ["amount_total:sum"], ["date_order:month"], orderby="date_order asc",
        )
        months = []
        for group in monthly_groups:
            months.append({
                "period": group.get("date_order:month") or "Undefined",
                "actual": round(group.get("amount_total") or 0.0, 2),
            })
        month_target = round(target / len(months), 2) if months and target else 0.0
        for month in months:
            month["target"] = month_target
            month["achievement"] = round(month["actual"] / month_target * 100, 2) if month_target else 0.0

        return {
            "overall": {"target": target, "actual": actual, "achievement": achievement, "remaining": remaining},
            "monthly": months,
        }
