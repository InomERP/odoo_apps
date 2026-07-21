# -*- coding: utf-8 -*-
# Part of InomERP. See LICENSE file for full copyright and licensing details.
# Copyright (C) InomERP Pvt Ltd (<https://inomerp.in>).
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models


class UnivAdmissionDashboard(models.TransientModel):
    """Dedicated, self-contained model for the Admissions Dashboard.

    Kept separate from ``univ.applicant`` so that dashboard analytics never
    interfere with the application model or its workflow. All methods are
    strictly read-only aggregations over existing applicant records.
    """

    _name = "univ.admission.dashboard"
    _description = "Admissions Dashboard"

    def _dashboard_date_domain(self, date_range, today):
        """Domain fragment for the requested submission-date range."""
        if date_range == "today":
            return [("applied_date", "=", today)]
        if date_range == "week":
            week_start = today - relativedelta(days=today.weekday())
            return [("applied_date", ">=", week_start)]
        if date_range == "month":
            return [("applied_date", ">=", today.replace(day=1))]
        return []

    @api.model
    def get_admissions_dashboard_data(self, date_range="all", program_id=False):
        """Aggregated, read-only data for the Admissions Dashboard."""
        today = fields.Date.context_today(self)
        base = []
        if program_id:
            base.append(("program_id", "=", int(program_id)))
        scoped = base + self._dashboard_date_domain(date_range, today)

        Applicant = self.env["univ.applicant"].sudo()

        def count(extra):
            return Applicant.search_count(scoped + extra)

        month_start = today.replace(day=1)
        kpis = {
            "total": Applicant.search_count(scoped),
            "today": Applicant.search_count(scoped + [("applied_date", "=", today)]),
            "month": Applicant.search_count(
                scoped + [("applied_date", ">=", month_start)]
            ),
            "verification": count([("stage_id.code", "=", "document_verification")]),
            "offers": count([("offer_state", "in", ["sent", "accepted"])]),
            "confirmed": count([("is_enrolled", "=", True)]),
            "rejected": count([("stage_id.is_rejected", "=", True)]),
        }

        # Program-wise distribution (bar chart).
        prog_groups = Applicant._read_group(
            scoped, groupby=["program_id"], aggregates=["__count"]
        )
        programs = sorted(
            [{
                "id": prog.id if prog else False,
                "label": prog.display_name if prog else "Unassigned",
                "value": cnt,
            } for prog, cnt in prog_groups],
            key=lambda r: r["value"], reverse=True,
        )

        # Status distribution by pipeline stage (donut chart).
        stage_groups = Applicant._read_group(
            scoped, groupby=["stage_id"], aggregates=["__count"]
        )
        statuses = sorted(
            [{
                "id": stage.id if stage else False,
                "label": stage.display_name if stage else "Unassigned",
                "value": cnt,
            } for stage, cnt in stage_groups],
            key=lambda r: r["value"], reverse=True,
        )

        # Admission trend over the last 6 months (uses the program filter).
        trend = []
        for offset in range(5, -1, -1):
            m_start = month_start - relativedelta(months=offset)
            m_end = m_start + relativedelta(months=1)
            trend.append({
                "label": m_start.strftime("%b %y"),
                "value": Applicant.search_count(
                    base + [("applied_date", ">=", m_start),
                            ("applied_date", "<", m_end)]
                ),
            })

        # Recent applications (clickable table).
        recent = []
        for rec in Applicant.search(
            scoped, limit=10, order="applied_date desc, id desc"
        ):
            recent.append({
                "id": rec.id,
                "application_no": rec.application_no or "",
                "name": rec.name or "",
                "program": rec.program_id.display_name or "",
                "stage": rec.stage_id.display_name or "",
                "applied_date": (
                    fields.Date.to_string(rec.applied_date)
                    if rec.applied_date else ""
                ),
            })

        all_programs = [
            {"id": p.id, "name": p.display_name}
            for p in self.env["univ.program"].sudo().search([], order="name")
        ]

        return {
            "kpis": kpis,
            "programs": programs,
            "statuses": statuses,
            "trend": trend,
            "recent": recent,
            "all_programs": all_programs,
        }
