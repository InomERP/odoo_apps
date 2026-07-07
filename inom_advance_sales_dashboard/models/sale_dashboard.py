# -*- coding: utf-8 -*-
from odoo import api, models


class SaleDashboard(models.AbstractModel):
    """Sales dashboard data provider.

    Phase 2 - Data Aggregation Backend.

    This abstract model hosts the single aggregation entry point
    ``get_dashboard_data`` which reads confirmed sale orders and their lines
    and returns one JSON-serialisable payload containing the data for every
    dashboard widget defined in the SRS (W-01 to W-10 and W-12, plus the
    actual sales figures required by W-11).

    Scope notes (strictly Phase 2):
      * Only backend aggregation is implemented here.
      * Revenue Target Achievement (W-11) target logic is NOT implemented;
        only the actual per-team revenue is returned for future use (Phase 4).
      * No charts, filters, reports or UI changes are part of this phase.

    Revenue basis (fixed once here and used consistently, per SRS section 7):
      * Order-level revenue  -> ``sale.order.amount_total``.
      * Line-level revenue   -> ``sale.order.line.price_subtotal``.

    Only confirmed orders are considered (state in ``sale`` / ``done``);
    draft and cancelled orders are excluded.
    """

    _name = "sale.dashboard"
    _description = "Sales Dashboard Data Provider"

    # Confirmed sale order states used as the revenue basis.
    _CONFIRMED_STATES = ["sale", "done"]

    # ------------------------------------------------------------------
    # Domain helpers
    # ------------------------------------------------------------------
    def _get_filter_leaves(self, prefix=""):
        """Return additive domain leaves for the optional advanced filters.

        Filters are read from the context key ``inom_dashboard_filters`` (set by
        ``get_dashboard_data``). When no filters are provided this returns an
        empty list, so existing behaviour is unchanged. ``prefix`` is "" for
        ``sale.order`` domains and "order_id." for ``sale.order.line`` domains.
        """
        filters = self.env.context.get("inom_dashboard_filters") or {}
        leaves = []
        if filters.get("salesperson_ids"):
            leaves.append((prefix + "user_id", "in", filters["salesperson_ids"]))
        if filters.get("team_ids"):
            leaves.append((prefix + "team_id", "in", filters["team_ids"]))
        if filters.get("partner_ids"):
            leaves.append((prefix + "partner_id", "in", filters["partner_ids"]))
        if filters.get("company_ids"):
            leaves.append((prefix + "company_id", "in", filters["company_ids"]))
        if filters.get("category_ids"):
            if prefix:
                leaves.append(("product_id.categ_id", "in", filters["category_ids"]))
            else:
                leaves.append(("order_line.product_id.categ_id", "in", filters["category_ids"]))
        return leaves

    def _get_order_domain(self, date_from=None, date_to=None):
        """Return the base domain for confirmed sale orders.

        :param date_from: optional lower bound (inclusive) on ``date_order``.
        :param date_to: optional upper bound (inclusive) on ``date_order``.
        :return: an Odoo domain (list of tuples).
        """
        domain = [("state", "in", self._CONFIRMED_STATES)]
        if date_from:
            domain.append(("date_order", ">=", date_from))
        if date_to:
            domain.append(("date_order", "<=", date_to))
        domain += self._get_filter_leaves(prefix="")
        return domain

    def _get_line_domain(self, date_from=None, date_to=None):
        """Return the base domain for lines of confirmed sale orders.

        Section/note lines (no product) are excluded so that only real
        product lines are aggregated.
        """
        domain = [
            ("order_id.state", "in", self._CONFIRMED_STATES),
            ("product_id", "!=", False),
        ]
        if date_from:
            domain.append(("order_id.date_order", ">=", date_from))
        if date_to:
            domain.append(("order_id.date_order", "<=", date_to))
        domain += self._get_filter_leaves(prefix="order_id.")
        return domain

    def _get_dashboard_timezone(self):
        """Return a PostgreSQL-safe timezone name for date grouping.

        Date-granularity grouping (for example ``date_order:month``) makes
        PostgreSQL convert the stored UTC datetime to the context timezone
        using ``AT TIME ZONE``. Some PostgreSQL installations ship a timezone
        database without the legacy ``Asia/Calcutta`` alias, which raises
        ``time zone "Asia/Calcutta" not recognized``. This helper resolves the
        active timezone and normalises that deprecated alias to its canonical
        name ``Asia/Kolkata`` so the grouping never fails.
        """
        tz = self.env.context.get("tz") or self.env.user.tz or "UTC"
        if tz == "Asia/Calcutta":
            tz = "Asia/Kolkata"
        return tz

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------
    @api.model
    def get_dashboard_data(self, date_from=None, date_to=None, filters=None):
        """Return the complete dashboard payload as a single dictionary.

        The optional ``date_from`` / ``date_to`` parameters define the
        reporting window. When omitted, all confirmed orders are considered.

        The optional ``filters`` dict adds advanced filtering and may contain
        ``salesperson_ids``, ``team_ids``, ``partner_ids``, ``company_ids`` and
        ``category_ids`` (lists of ids). It is applied additively to the domains
        via the context; when empty, behaviour is identical to before.

        :return: dict keyed by widget with JSON-serialisable values.
        """
        if filters:
            self = self.with_context(inom_dashboard_filters=filters)
        currency = self.env.company.currency_id

        payload = {
            "currency": {
                "id": currency.id,
                "name": currency.name,
                "symbol": currency.symbol,
            },
            "period": {
                "date_from": date_from or False,
                "date_to": date_to or False,
            },
            # W-01
            "summary": self._get_summary(date_from, date_to),
            # W-02
            "monthly_revenue": self._get_monthly_revenue(date_from, date_to),
            # W-03 / W-04 / W-05
            **self._get_customer_mix(date_from, date_to),
            # W-06
            "top_products_revenue": self._get_top_products_by_revenue(date_from, date_to),
            # W-07
            "revenue_by_category": self._get_revenue_by_category(date_from, date_to),
            # W-08
            "sales_by_salesperson": self._get_sales_by_salesperson(date_from, date_to),
            # W-09
            "sales_by_country": self._get_sales_by_country(date_from, date_to),
            # W-10
            "top_products_volume": self._get_top_products_by_volume(date_from, date_to),
            # W-11 (actuals only; target logic is Phase 4)
            "sales_by_team": self._get_sales_by_team(date_from, date_to),
            # W-12
            "top_customers": self._get_top_customers_by_revenue(date_from, date_to),
        }
        return payload

    # ------------------------------------------------------------------
    # W-01 - Total Revenue & Total Sale Orders
    # ------------------------------------------------------------------
    def _get_summary(self, date_from=None, date_to=None):
        orders = self.env["sale.order"]
        domain = self._get_order_domain(date_from, date_to)
        groups = orders.read_group(domain, ["amount_total:sum"], [])
        total_revenue = 0.0
        total_orders = 0
        if groups:
            total_revenue = groups[0].get("amount_total") or 0.0
            total_orders = groups[0].get("__count") or 0
        return {
            "total_revenue": round(total_revenue, 2),
            "total_orders": total_orders,
        }

    # ------------------------------------------------------------------
    # W-02 - Monthly Revenue Trend
    # ------------------------------------------------------------------
    def _get_monthly_revenue(self, date_from=None, date_to=None):
        # A safe timezone context is applied because month-level grouping
        # converts datetimes using AT TIME ZONE in PostgreSQL.
        orders = self.env["sale.order"].with_context(tz=self._get_dashboard_timezone())
        domain = self._get_order_domain(date_from, date_to)
        groups = orders.read_group(
            domain,
            ["amount_total:sum"],
            ["date_order:month"],
            orderby="date_order asc",
        )
        result = []
        for group in groups:
            result.append({
                "period": group.get("date_order:month") or "Undefined",
                "revenue": round(group.get("amount_total") or 0.0, 2),
            })
        return result

    # ------------------------------------------------------------------
    # W-03 / W-04 / W-05 - New vs Repeat customers and their order share
    # ------------------------------------------------------------------
    def _get_customer_mix(self, date_from=None, date_to=None):
        orders = self.env["sale.order"]
        domain = self._get_order_domain(date_from, date_to)

        # Customers active in the period, with their order counts.
        partner_groups = orders.read_group(domain, ["partner_id"], ["partner_id"])
        active_partner_ids = [
            g["partner_id"][0] for g in partner_groups if g.get("partner_id")
        ]
        order_count_by_partner = {
            g["partner_id"][0]: (g.get("__count") or 0)
            for g in partner_groups
            if g.get("partner_id")
        }
        total_orders = sum(order_count_by_partner.values())
        total_customers = len(active_partner_ids)

        # A customer is "repeat" if they have a confirmed order strictly before
        # the period start. Without a period start, no customer qualifies as
        # repeat (every active customer is new).
        repeat_partner_ids = set()
        if date_from and active_partner_ids:
            prior_domain = [
                ("state", "in", self._CONFIRMED_STATES),
                ("partner_id", "in", active_partner_ids),
                ("date_order", "<", date_from),
            ]
            prior_domain += self._get_filter_leaves(prefix="")
            prior_groups = orders.read_group(prior_domain, ["partner_id"], ["partner_id"])
            repeat_partner_ids = {
                g["partner_id"][0] for g in prior_groups if g.get("partner_id")
            }

        new_partner_ids = set(active_partner_ids) - repeat_partner_ids

        new_customers = len(new_partner_ids)
        repeat_customers = len(repeat_partner_ids)

        pct_new = round(new_customers / total_customers * 100, 2) if total_customers else 0.0
        pct_repeat = round(repeat_customers / total_customers * 100, 2) if total_customers else 0.0

        # W-04 / W-05 - share of orders by customer group.
        new_order_count = sum(
            cnt for pid, cnt in order_count_by_partner.items() if pid in new_partner_ids
        )
        repeat_order_count = sum(
            cnt for pid, cnt in order_count_by_partner.items() if pid in repeat_partner_ids
        )
        pct_orders_new = round(new_order_count / total_orders * 100, 2) if total_orders else 0.0
        pct_orders_repeat = round(repeat_order_count / total_orders * 100, 2) if total_orders else 0.0

        return {
            "customer_mix": {
                "total_customers": total_customers,
                "new_customers": new_customers,
                "repeat_customers": repeat_customers,
                "pct_new": pct_new,
                "pct_repeat": pct_repeat,
            },
            "orders_from_new_pct": pct_orders_new,
            "orders_from_repeat_pct": pct_orders_repeat,
        }

    # ------------------------------------------------------------------
    # W-06 - Top 5 Products by Revenue
    # ------------------------------------------------------------------
    def _get_top_products_by_revenue(self, date_from=None, date_to=None):
        lines = self.env["sale.order.line"]
        domain = self._get_line_domain(date_from, date_to)
        groups = lines.read_group(
            domain,
            ["price_subtotal:sum"],
            ["product_id"],
            orderby="price_subtotal desc",
            limit=5,
        )
        return [
            {
                "product_id": g["product_id"][0],
                "product_name": g["product_id"][1],
                "revenue": round(g.get("price_subtotal") or 0.0, 2),
            }
            for g in groups
            if g.get("product_id")
        ]

    # ------------------------------------------------------------------
    # W-07 - Revenue by Product Category
    # ------------------------------------------------------------------
    def _get_revenue_by_category(self, date_from=None, date_to=None):
        lines = self.env["sale.order.line"]
        domain = self._get_line_domain(date_from, date_to)
        groups = lines.read_group(domain, ["price_subtotal:sum"], ["product_id"])

        product_ids = [g["product_id"][0] for g in groups if g.get("product_id")]
        products = self.env["product.product"].browse(product_ids)
        product_to_category = {
            product.id: (
                product.categ_id.id,
                product.categ_id.display_name or "Undefined",
            )
            for product in products
        }

        category_revenue = {}
        for group in groups:
            if not group.get("product_id"):
                continue
            product_id = group["product_id"][0]
            category = product_to_category.get(product_id, (False, "Undefined"))
            revenue = group.get("price_subtotal") or 0.0
            category_revenue.setdefault(category, 0.0)
            category_revenue[category] += revenue

        result = [
            {
                "category_id": category[0],
                "category_name": category[1],
                "revenue": round(revenue, 2),
            }
            for category, revenue in category_revenue.items()
        ]
        result.sort(key=lambda item: item["revenue"], reverse=True)
        return result

    # ------------------------------------------------------------------
    # W-08 - Sales by Salesperson
    # ------------------------------------------------------------------
    def _get_sales_by_salesperson(self, date_from=None, date_to=None):
        orders = self.env["sale.order"]
        domain = self._get_order_domain(date_from, date_to)
        groups = orders.read_group(
            domain,
            ["amount_total:sum"],
            ["user_id"],
            orderby="amount_total desc",
        )
        result = []
        for group in groups:
            user = group.get("user_id")
            result.append({
                "user_id": user[0] if user else False,
                "salesperson": user[1] if user else "Undefined",
                "revenue": round(group.get("amount_total") or 0.0, 2),
            })
        return result

    # ------------------------------------------------------------------
    # W-09 - Sales by Country
    # ------------------------------------------------------------------
    def _get_sales_by_country(self, date_from=None, date_to=None):
        orders = self.env["sale.order"]
        domain = self._get_order_domain(date_from, date_to)
        groups = orders.read_group(domain, ["amount_total:sum"], ["partner_id"])

        partner_ids = [g["partner_id"][0] for g in groups if g.get("partner_id")]
        partners = self.env["res.partner"].browse(partner_ids)
        partner_to_country = {
            partner.id: (
                partner.country_id.id,
                partner.country_id.name or "Undefined",
            )
            for partner in partners
        }

        country_revenue = {}
        for group in groups:
            if not group.get("partner_id"):
                continue
            partner_id = group["partner_id"][0]
            country = partner_to_country.get(partner_id, (False, "Undefined"))
            revenue = group.get("amount_total") or 0.0
            country_revenue.setdefault(country, 0.0)
            country_revenue[country] += revenue

        result = [
            {
                "country_id": country[0],
                "country": country[1],
                "revenue": round(revenue, 2),
            }
            for country, revenue in country_revenue.items()
        ]
        result.sort(key=lambda item: item["revenue"], reverse=True)
        return result

    # ------------------------------------------------------------------
    # W-10 - Top 5 Products by Sales Quantity
    # ------------------------------------------------------------------
    def _get_top_products_by_volume(self, date_from=None, date_to=None):
        lines = self.env["sale.order.line"]
        domain = self._get_line_domain(date_from, date_to)
        groups = lines.read_group(
            domain,
            ["product_uom_qty:sum"],
            ["product_id"],
            orderby="product_uom_qty desc",
            limit=5,
        )
        return [
            {
                "product_id": g["product_id"][0],
                "product_name": g["product_id"][1],
                "quantity": round(g.get("product_uom_qty") or 0.0, 2),
            }
            for g in groups
            if g.get("product_id")
        ]

    # ------------------------------------------------------------------
    # W-11 - Revenue Target Achievement (actual vs configured target)
    # ------------------------------------------------------------------
    def _get_targets_by_team(self, date_from=None, date_to=None):
        """Return the total configured target amount per sales team.

        Targets whose ``[period_start, period_end]`` window overlaps the
        selected ``[date_from, date_to]`` window are summed per team. When no
        window is selected, every target is considered.

        :return: dict mapping ``team_id`` -> summed target amount.
        """
        target_model = self.env["inom.sales.target"]
        domain = []
        # Two date ranges overlap when start_a <= end_b and end_a >= start_b.
        if date_to:
            domain.append(("period_start", "<=", date_to))
        if date_from:
            domain.append(("period_end", ">=", date_from))

        # Respect the team / company advanced filters on targets too.
        adv = self.env.context.get("inom_dashboard_filters") or {}
        if adv.get("team_ids"):
            domain.append(("team_id", "in", adv["team_ids"]))
        if adv.get("company_ids"):
            domain.append(("company_id", "in", adv["company_ids"]))

        totals = {}
        for target in target_model.search(domain):
            if not target.team_id:
                continue
            totals.setdefault(target.team_id.id, 0.0)
            totals[target.team_id.id] += target.target_amount
        return totals

    def _get_sales_by_team(self, date_from=None, date_to=None):
        orders = self.env["sale.order"]
        domain = self._get_order_domain(date_from, date_to)
        groups = orders.read_group(
            domain,
            ["amount_total:sum"],
            ["team_id"],
            orderby="amount_total desc",
        )

        actual_by_team = {}
        team_names = {}
        for group in groups:
            team = group.get("team_id")
            team_id = team[0] if team else False
            actual_by_team[team_id] = round(group.get("amount_total") or 0.0, 2)
            team_names[team_id] = team[1] if team else "Undefined"

        target_by_team = self._get_targets_by_team(date_from, date_to)

        # Include every team that has either sales or a configured target so
        # achievement is shown even when one side is missing.
        all_team_ids = set(actual_by_team) | set(target_by_team)

        # Resolve names for target-only teams (no sales in the window).
        missing_ids = [tid for tid in all_team_ids if tid and tid not in team_names]
        if missing_ids:
            for team in self.env["crm.team"].browse(missing_ids):
                team_names[team.id] = team.display_name

        result = []
        for team_id in all_team_ids:
            actual = actual_by_team.get(team_id, 0.0)
            target = round(target_by_team.get(team_id, 0.0), 2)
            has_target = bool(target)
            achievement = round(actual / target * 100, 2) if has_target else 0.0
            result.append({
                "team_id": team_id or False,
                "team": team_names.get(team_id, "Undefined"),
                "actual_revenue": actual,
                "target_amount": target,
                "achievement_pct": achievement,
                "has_target": has_target,
            })
        result.sort(key=lambda item: item["actual_revenue"], reverse=True)
        return result

    # ------------------------------------------------------------------
    # W-12 - Top 5 Customers by Revenue
    # ------------------------------------------------------------------
    def _get_top_customers_by_revenue(self, date_from=None, date_to=None):
        orders = self.env["sale.order"]
        domain = self._get_order_domain(date_from, date_to)
        groups = orders.read_group(
            domain,
            ["amount_total:sum"],
            ["partner_id"],
            orderby="amount_total desc",
            limit=5,
        )
        return [
            {
                "partner_id": g["partner_id"][0],
                "customer": g["partner_id"][1],
                "revenue": round(g.get("amount_total") or 0.0, 2),
            }
            for g in groups
            if g.get("partner_id")
        ]
