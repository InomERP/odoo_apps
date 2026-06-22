# -*- coding: utf-8 -*-
from datetime import datetime, time

import pytz

from odoo import fields, http, _
from odoo.http import request

from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager


class InomPortalAttendance(CustomerPortal):
    """Website portal area that lets an employee manage their own attendance.

    Every database operation is scoped to the employee linked to the current
    portal user, so a user can never read or alter another employee's records.
    """

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _inom_attendance_enabled(self):
        """Return True when the feature is switched on in the settings."""
        get_param = request.env["ir.config_parameter"].sudo().get_param
        return get_param("inom_portal_attendance.enabled") in (
            "True", "true", "1", 1, True,
        )

    def _inom_time_format(self):
        get_param = request.env["ir.config_parameter"].sudo().get_param
        return get_param("inom_portal_attendance.time_format") or "24"

    def _inom_calc_method(self):
        get_param = request.env["ir.config_parameter"].sudo().get_param
        return get_param("inom_portal_attendance.calc_method") or "odoo"

    def _inom_get_employee(self):
        """Return the employee record tied to the connected portal user.

        Uses sudo because a portal user usually has no read access to
        ``hr.employee``; the search is still restricted to their own user id.
        """
        return request.env["hr.employee"].sudo().search(
            [("user_id", "=", request.env.user.id)], limit=1
        )

    def _inom_attendance_domain(self, employee):
        """Base domain restricting attendance records to one employee."""
        return [("employee_id", "=", employee.id)]

    def _inom_user_timezone(self):
        """Resolve the timezone used to render datetimes on the portal."""
        tz_name = request.env.user.tz or "UTC"
        try:
            return pytz.timezone(tz_name)
        except pytz.UnknownTimeZoneError:
            return pytz.UTC

    def _inom_localize(self, utc_dt):
        """Convert a naive UTC datetime to the user's local timezone."""
        if not utc_dt:
            return False
        local_tz = self._inom_user_timezone()
        return pytz.UTC.localize(utc_dt).astimezone(local_tz)

    def _inom_format_datetime(self, utc_dt):
        """Format a stored UTC datetime for display, honouring the time format."""
        local_dt = self._inom_localize(utc_dt)
        if not local_dt:
            return ""
        time_pattern = "%I:%M %p" if self._inom_time_format() == "12" else "%H:%M"
        return local_dt.strftime("%d %b %Y " + time_pattern)

    def _inom_format_hours(self, value):
        """Turn a float number of hours into a HH:MM:SS string."""
        value = value or 0.0
        if value < 0:
            value = 0.0
        total_seconds = int(round(value * 3600))
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return "%02d:%02d:%02d" % (hours, minutes, seconds)

    def _inom_extra_hours(self, attendance, employee):
        """Compute the extra hours according to the configured method."""
        if self._inom_calc_method() == "portal_avg":
            calendar = employee.resource_calendar_id
            average = calendar.hours_per_day if calendar else 0.0
            return max(attendance.worked_hours - average, 0.0)
        # Native Odoo flow: reuse the validated overtime already computed.
        return attendance.validated_overtime_hours

    def _inom_prepare_line(self, attendance, employee):
        """Build the display dictionary for a single attendance record."""
        return {
            "record": attendance,
            "check_in": self._inom_format_datetime(attendance.check_in),
            "check_out": self._inom_format_datetime(attendance.check_out)
            if attendance.check_out else "",
            "worked_hours": self._inom_format_hours(attendance.worked_hours),
            "extra_hours": self._inom_format_hours(
                self._inom_extra_hours(attendance, employee)
            ),
            "is_open": not attendance.check_out,
        }

    def _inom_open_attendance(self, employee):
        """Return the running (not yet checked out) attendance, if any."""
        return request.env["hr.attendance"].sudo().search(
            [("employee_id", "=", employee.id), ("check_out", "=", False)],
            limit=1,
        )

    # ------------------------------------------------------------------
    # Portal home card
    # ------------------------------------------------------------------
    def _prepare_portal_layout_values(self):
        values = super()._prepare_portal_layout_values()
        # Flag consumed by the inherited portal home template to decide whether
        # the attendance card is shown. It depends on the feature being enabled
        # and the connected user being an employee.
        values["inom_attendance_show_card"] = bool(
            self._inom_attendance_enabled() and self._inom_get_employee()
        )
        return values

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if "inom_attendance_count" in counters:
            employee = self._inom_get_employee()
            if self._inom_attendance_enabled() and employee:
                values["inom_attendance_count"] = request.env["hr.attendance"].sudo().search_count(
                    self._inom_attendance_domain(employee)
                )
            else:
                values["inom_attendance_count"] = 0
        return values

    # ------------------------------------------------------------------
    # Search bar configuration
    # ------------------------------------------------------------------
    def _inom_searchbar_sortings(self):
        return {
            "date": {"label": _("Check In"), "order": "check_in desc"},
            "worked": {"label": _("Worked Hours"), "order": "worked_hours desc"},
        }

    def _inom_searchbar_groupby(self):
        return {
            "none": {"label": _("None"), "input": "none"},
            "week": {"label": _("Week"), "input": "week"},
            "month": {"label": _("Month"), "input": "month"},
        }

    # ------------------------------------------------------------------
    # Routes
    # ------------------------------------------------------------------
    @http.route(["/my/attendance"], type="http", auth="user", website=True)
    def inom_portal_attendance(self, page=1, sortby=None, groupby=None,
                               date_begin=None, date_end=None, **kw):
        if not self._inom_attendance_enabled():
            return request.redirect("/my")

        employee = self._inom_get_employee()
        values = self._prepare_portal_layout_values()

        if not employee:
            values.update({
                "page_name": "inom_attendance",
                "no_employee": True,
                "attendances": [],
            })
            return request.render(
                "inom_portal_attendance.portal_my_attendance", values
            )

        Attendance = request.env["hr.attendance"].sudo()
        domain = self._inom_attendance_domain(employee)

        # Date range filter (values are plain date strings from the form).
        local_tz = self._inom_user_timezone()
        if date_begin:
            try:
                start = local_tz.localize(
                    datetime.combine(fields.Date.from_string(date_begin), time.min)
                ).astimezone(pytz.UTC).replace(tzinfo=None)
                domain += [("check_in", ">=", start)]
            except (ValueError, TypeError):
                date_begin = None
        if date_end:
            try:
                end = local_tz.localize(
                    datetime.combine(fields.Date.from_string(date_end), time.max)
                ).astimezone(pytz.UTC).replace(tzinfo=None)
                domain += [("check_in", "<=", end)]
            except (ValueError, TypeError):
                date_end = None

        # Sorting
        searchbar_sortings = self._inom_searchbar_sortings()
        if sortby not in searchbar_sortings:
            sortby = "date"
        order = searchbar_sortings[sortby]["order"]

        # Grouping
        searchbar_groupby = self._inom_searchbar_groupby()
        if groupby not in searchbar_groupby:
            groupby = "none"

        attendance_count = Attendance.search_count(domain)
        pager = portal_pager(
            url="/my/attendance",
            url_args={
                "sortby": sortby,
                "groupby": groupby,
                "date_begin": date_begin,
                "date_end": date_end,
            },
            total=attendance_count,
            page=page,
            step=self._items_per_page,
        )

        records = Attendance.search(
            domain, order=order, limit=self._items_per_page, offset=pager["offset"]
        )

        lines = [self._inom_prepare_line(rec, employee) for rec in records]
        grouped_lines = self._inom_group_lines(lines, groupby)

        values.update({
            "page_name": "inom_attendance",
            "employee": employee,
            "attendances": lines,
            "grouped_attendances": grouped_lines,
            "pager": pager,
            "sortby": sortby,
            "groupby": groupby,
            "date_begin": date_begin,
            "date_end": date_end,
            "searchbar_sortings": searchbar_sortings,
            "searchbar_groupby": searchbar_groupby,
            "open_attendance": self._inom_open_attendance(employee),
            "default_url": "/my/attendance",
        })
        return request.render(
            "inom_portal_attendance.portal_my_attendance", values
        )

    def _inom_group_lines(self, lines, groupby):
        """Group the prepared lines by week or month for display."""
        if groupby == "none":
            return [{"label": "", "lines": lines}]

        buckets = {}
        order = []
        for line in lines:
            check_in = line["record"].check_in
            local_dt = self._inom_localize(check_in)
            if groupby == "week":
                iso = local_dt.isocalendar()
                key = _("Week %(week)s, %(year)s") % {
                    "week": iso[1], "year": iso[0],
                }
            else:  # month
                key = local_dt.strftime("%B %Y")
            if key not in buckets:
                buckets[key] = []
                order.append(key)
            buckets[key].append(line)
        return [{"label": key, "lines": buckets[key]} for key in order]

    @http.route(["/my/attendance/check_in"], type="http", auth="user",
                website=True, methods=["POST"])
    def inom_portal_attendance_check_in(self, **post):
        if not self._inom_attendance_enabled():
            return request.redirect("/my")
        employee = self._inom_get_employee()
        if employee and not self._inom_open_attendance(employee):
            request.env["hr.attendance"].sudo().create({
                "employee_id": employee.id,
                "check_in": fields.Datetime.now(),
                "in_mode": "manual",
            })
        return request.redirect("/my/attendance")

    @http.route(["/my/attendance/check_out"], type="http", auth="user",
                website=True, methods=["POST"])
    def inom_portal_attendance_check_out(self, **post):
        if not self._inom_attendance_enabled():
            return request.redirect("/my")
        employee = self._inom_get_employee()
        if employee:
            open_attendance = self._inom_open_attendance(employee)
            if open_attendance:
                open_attendance.write({
                    "check_out": fields.Datetime.now(),
                    "out_mode": "manual",
                })
        return request.redirect("/my/attendance")

    @http.route(["/my/attendance/<int:attendance_id>"], type="http",
                auth="user", website=True)
    def inom_portal_attendance_detail(self, attendance_id, **kw):
        if not self._inom_attendance_enabled():
            return request.redirect("/my")
        employee = self._inom_get_employee()
        if not employee:
            return request.redirect("/my/attendance")

        attendance = request.env["hr.attendance"].sudo().browse(attendance_id)

        # Ownership guard: never expose another employee's record. This explicit
        # check is the security boundary, independent of record rules.
        if not attendance.exists() or attendance.employee_id.id != employee.id:
            return request.redirect("/my/attendance")

        values = self._prepare_portal_layout_values()
        values.update({
            "page_name": "inom_attendance",
            "employee": employee,
            "attendance": attendance,
            "line": self._inom_prepare_line(attendance, employee),
        })
        return request.render(
            "inom_portal_attendance.portal_attendance_detail", values
        )
