# -*- coding: utf-8 -*-
from datetime import datetime, time, timedelta

import pytz

from odoo import api, fields, models, tools, _

# Our own models must never be audited (would recurse / create noise).
AUDIT_MODELS = ("inom.audit.trail.rule", "inom.audit.trail.log", "inom.audit.trail.log.line")

METHOD_FLAG = {
    "create": "log_create",
    "read": "log_read",
    "write": "log_write",
    "unlink": "log_unlink",
}


class AuditTrailRule(models.Model):
    _name = "inom.audit.trail.rule"
    _description = "Audit Trail Logging Rule"
    _order = "name"

    name = fields.Char(required=True)
    model_id = fields.Many2one(
        "ir.model", string="Object (Model)", required=True, ondelete="cascade",
        help="The Odoo object whose activity should be tracked.")
    model_name = fields.Char(
        related="model_id.model", string="Technical Model", store=True, index=True)

    log_create = fields.Boolean(string="Log Creation", default=True)
    log_read = fields.Boolean(string="Log Read Access", default=False)
    log_write = fields.Boolean(string="Log Update", default=True)
    log_unlink = fields.Boolean(string="Log Deletion", default=True)

    field_ids = fields.Many2many(
        "ir.model.fields", string="Tracked Fields",
        domain="[('model_id', '=', model_id)]",
        help="Fields watched on Update. Each change is stored with the user, "
             "the old value and the new value. Leave empty to track every field.")
    group_id = fields.Many2one(
        "res.groups", string="Restrict to Group",
        help="Only log actions performed by users in this group. "
             "Empty = all users.")

    active = fields.Boolean(default=True)
    log_count = fields.Integer(string="Logged", compute="_compute_log_count")

    _sql_constraints = [
        ("model_uniq", "unique(model_id)",
         "A logging rule already exists for this object. Edit the existing one."),
    ]

    # ------------------------------------------------------------------
    # Computed / onchange
    # ------------------------------------------------------------------
    def _compute_log_count(self):
        Log = self.env["inom.audit.trail.log"]
        for rule in self:
            rule.log_count = Log.search_count(
                [("rule_id", "=", rule.id)]) if rule.id else 0

    @api.onchange("model_id")
    def _onchange_model_id(self):
        # tracked fields belong to the selected model only
        self.field_ids = False

    def action_view_logs(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Audit Logs"),
            "res_model": "inom.audit.trail.log",
            "view_mode": "list,form",
            "domain": [("rule_id", "=", self.id)],
            "context": {"create": False},
        }

    # ------------------------------------------------------------------
    # Cache: which rules exist per model (shared across users)
    # ------------------------------------------------------------------
    @api.model
    @tools.ormcache("model_name")
    def _audit_rule_ids_for_model(self, model_name):
        return self.sudo().search([("model_name", "=", model_name)]).ids

    @api.model
    def _audit_clear_cache(self):
        registry = self.env.registry
        if hasattr(registry, "clear_cache"):
            registry.clear_cache()
        elif hasattr(registry, "clear_caches"):
            registry.clear_caches()

    @api.model
    def _audit_get_rules(self, model_name, method):
        """Active rules that cover (model_name, method) for the *current* user.

        Returns a **sudo** recordset: logging is a system activity, so normal
        users must never need read access to the rule model themselves.
        """
        ids = self._audit_rule_ids_for_model(model_name)
        if not ids:
            return self.sudo().browse()
        rules = self.sudo().browse(ids).exists().filtered("active")
        flag = METHOD_FLAG[method]
        user_group_ids = set(self.env.user.groups_id.ids)
        return rules.filtered(
            lambda r: r[flag] and (not r.group_id or r.group_id.id in user_group_ids)
        )

    # invalidate the cache whenever rules change
    @api.model_create_multi
    def create(self, vals_list):
        rules = super().create(vals_list)
        self._audit_clear_cache()
        return rules

    def write(self, vals):
        res = super().write(vals)
        self._audit_clear_cache()
        return res

    def unlink(self):
        res = super().unlink()
        self._audit_clear_cache()
        return res

    # ------------------------------------------------------------------
    # Request / session context (IP, browser, location)
    # ------------------------------------------------------------------
    @api.model
    def _audit_parse_ua(self, ua):
        if not ua:
            return ""
        s = ua.lower()
        if "edg/" in s or "edge" in s:
            browser = "Edge"
        elif "opr/" in s or "opera" in s:
            browser = "Opera"
        elif "chromium" in s:
            browser = "Chromium"
        elif "chrome" in s:
            browser = "Chrome"
        elif "firefox" in s:
            browser = "Firefox"
        elif "safari" in s:
            browser = "Safari"
        else:
            browser = "Other"
        if "windows" in s:
            os_name = "Windows"
        elif "android" in s:
            os_name = "Android"
        elif "iphone" in s or "ipad" in s or " ios" in s:
            os_name = "iOS"
        elif "mac os" in s or "macintosh" in s:
            os_name = "macOS"
        elif "linux" in s:
            os_name = "Linux"
        else:
            os_name = ""
        return ("%s · %s" % (browser, os_name)) if os_name else browser

    @api.model
    def _audit_request_info(self):
        """Best-effort capture of the current HTTP request context. Returns
        empty values when there is no request (cron, server actions, tests)."""
        info = {"ip_address": "", "user_agent": "", "browser": "", "location": ""}
        try:
            from odoo.http import request
            if not request:
                return info
            httpreq = getattr(request, "httprequest", None)
            if httpreq is not None:
                # real client IP (first entry of X-Forwarded-For when behind a proxy)
                xff = httpreq.headers.get("X-Forwarded-For", "")
                ip = (xff.split(",")[0].strip() if xff else "") or httpreq.remote_addr or ""
                info["ip_address"] = ip
                ua = httpreq.headers.get("User-Agent", "") or ""
                info["user_agent"] = ua[:512]
                info["browser"] = self._audit_parse_ua(ua)
            # GeoIP is optional: only populated if a GeoIP database is configured
            geo = getattr(request, "geoip", None)
            if geo:
                city = country = ""
                try:
                    city = geo.get("city") or ""
                    country = geo.get("country_name") or ""
                except Exception:
                    city = getattr(geo, "city", "") or ""
                    country = getattr(geo, "country_name", "") or ""
                info["location"] = ", ".join([p for p in (city, country) if p])
        except Exception:
            pass
        return info

    @api.model
    def _audit_presence_model(self):
        for name in ("bus.presence", "mail.presence"):
            if name in self.env:
                return self.env[name].sudo()
        return None

    # ------------------------------------------------------------------
    # Value formatting
    # ------------------------------------------------------------------
    @api.model
    def _audit_format_value(self, record, field_name):
        field = record._fields.get(field_name)
        if not field:
            return ""
        try:
            value = record[field_name]
        except Exception:
            return ""
        if field.type == "many2one":
            return value.display_name or "" if value else ""
        if field.type in ("many2many", "one2many"):
            return ", ".join(value.mapped("display_name")) if value else ""
        if value in (False, None) and field.type != "boolean":
            return ""
        return str(value)

    # ------------------------------------------------------------------
    # Loggers (called from the `base` override)
    # ------------------------------------------------------------------
    @api.model
    def _audit_log_simple(self, model_name, method, records):
        """Log create / read / unlink (no field lines)."""
        rules = self._audit_get_rules(model_name, method)
        if not rules or not records:
            return
        Log = self.env["inom.audit.trail.log"].sudo().with_context(inom_audit_trail_skip=True)
        model = self.env["ir.model"].sudo()._get(model_name)
        req = self._audit_request_info()
        rows = []
        for rule in rules:
            for rec in records:
                vals = {
                    "rule_id": rule.id,
                    "model_id": model.id,
                    "res_id": rec.id,
                    "res_name": rec.display_name,
                    "method": method,
                    "user_id": self.env.uid,
                }
                vals.update(req)
                rows.append(vals)
        if rows:
            Log.create(rows)

    @api.model
    def _audit_snapshot(self, model_name, records, vals):
        """Capture old values of the fields about to change. Returns None if
        nothing relevant is being tracked."""
        rules = self._audit_get_rules(model_name, "write")
        if not rules:
            return None
        candidates = set(vals.keys())
        track_all = any(not rule.field_ids for rule in rules)
        tracked = set()
        for rule in rules:
            tracked |= set(rule.field_ids.mapped("name"))
        watch = candidates if track_all else (candidates & tracked)
        watch = {f for f in watch if f in records._fields}
        if not watch:
            return None
        old = {}
        for rec in records:
            old[rec.id] = {f: self._audit_format_value(rec, f) for f in watch}
        return {"rules": rules, "watch": watch, "old": old}

    @api.model
    def _audit_log_write(self, model_name, records, snapshot):
        """Log update + one line per changed tracked field (old → new)."""
        if not snapshot:
            return
        rules = snapshot["rules"]
        Log = self.env["inom.audit.trail.log"].sudo().with_context(inom_audit_trail_skip=True)
        Line = self.env["inom.audit.trail.log.line"].sudo().with_context(inom_audit_trail_skip=True)
        IrField = self.env["ir.model.fields"].sudo()
        model = self.env["ir.model"].sudo()._get(model_name)
        req = self._audit_request_info()
        for rule in rules:
            tracked = set(rule.field_ids.mapped("name")) if rule.field_ids else None
            for rec in records:
                old_vals = snapshot["old"].get(rec.id, {})
                changes = []
                for fname, oldv in old_vals.items():
                    if tracked is not None and fname not in tracked:
                        continue
                    newv = self._audit_format_value(rec, fname)
                    if str(newv) != str(oldv):
                        changes.append((fname, oldv, newv))
                if not changes:
                    continue
                log = Log.create({
                    "rule_id": rule.id,
                    "model_id": model.id,
                    "res_id": rec.id,
                    "res_name": rec.display_name,
                    "method": "write",
                    "user_id": self.env.uid,
                    **req,
                })
                line_rows = []
                for fname, oldv, newv in changes:
                    fld = IrField._get(model_name, fname)
                    line_rows.append({
                        "log_id": log.id,
                        "field_id": fld.id if fld else False,
                        "field_name": fname,
                        "field_description": fld.field_description if fld else fname,
                        "old_value": oldv,
                        "new_value": newv,
                    })
                if line_rows:
                    Line.create(line_rows)

    # ------------------------------------------------------------------
    # Dashboard data (called over RPC from the OWL component)
    # ------------------------------------------------------------------
    @api.model
    def get_dashboard_data(self):
        Log = self.env["inom.audit.trail.log"].sudo()

        # --- active users right now ---
        # Reflect logout/idle promptly: a user counts as "online" only if their
        # canonical im_status is 'online' AND their presence was refreshed within
        # a short window. The person opening the dashboard always counts.
        ONLINE_WINDOW_MIN = 2
        candidates = self.env["res.users"].sudo().browse()
        presence = self._audit_presence_model()
        if presence is not None and "user_id" in presence._fields:
            field = ("last_poll" if "last_poll" in presence._fields
                     else ("last_presence" if "last_presence" in presence._fields else None))
            try:
                if field:
                    threshold = fields.Datetime.now() - timedelta(minutes=ONLINE_WINDOW_MIN)
                    recs = presence.search([(field, ">=", threshold)])
                else:
                    recs = presence.search([])
                candidates |= recs.mapped("user_id")
            except Exception:
                pass

        def _is_online(user):
            try:
                if "im_status" in user._fields and user.im_status not in ("online", "away"):
                    return False
            except Exception:
                pass
            return True

        online = candidates.filtered(lambda u: u and u.active and _is_online(u))
        # the person opening the dashboard is active right now, regardless
        online |= self.env.user
        online = online.filtered(lambda u: u and u.active)
        active_now = len(online)
        online_users = [{"id": u.id, "name": u.name} for u in online[:12]]

        # --- today vs yesterday (in the user's timezone) ---
        tz = pytz.timezone(self.env.user.tz or "UTC")
        now_local = datetime.now(tz)
        start_today_local = tz.localize(datetime.combine(now_local.date(), time.min))
        start_yest_local = start_today_local - timedelta(days=1)

        def to_utc_naive(dt):
            return dt.astimezone(pytz.UTC).replace(tzinfo=None)

        start_today = to_utc_naive(start_today_local)
        start_yest = to_utc_naive(start_yest_local)

        today_count = Log.search_count([("create_date", ">=", start_today)])
        yest_count = Log.search_count([
            ("create_date", ">=", start_yest),
            ("create_date", "<", start_today),
        ])

        # --- today's activity in 12 two-hour buckets (local time) ---
        buckets = [0] * 12
        for row in Log.search_read([("create_date", ">=", start_today)], ["create_date"]):
            cd = row["create_date"]
            if cd:
                local = pytz.UTC.localize(cd).astimezone(tz)
                buckets[min(11, local.hour // 2)] += 1

        rules = self.sudo().search([])
        active_rules = rules.filtered("active")

        # --- rules list for the dashboard panel ---
        rules_data = []
        for r in rules:
            rules_data.append({
                "id": r.id,
                "name": r.name,
                "model_label": r.model_id.name or "",
                "model_tech": r.model_name or "",
                "create": r.log_create,
                "read": r.log_read,
                "write": r.log_write,
                "unlink": r.log_unlink,
                "fields": r.field_ids.mapped("field_description")[:4],
                "fields_extra": max(0, len(r.field_ids) - 4),
                "fields_all": not r.field_ids,
                "group": r.group_id.name or "",
                "active": r.active,
                "log_count": Log.search_count([("rule_id", "=", r.id)]),
            })

        return {
            "active_now": active_now,
            "online_users": online_users,
            "today": today_count,
            "yesterday": yest_count,
            "buckets": buckets,
            "current_bucket": now_local.hour // 2,
            "active_rules": len(active_rules),
            "total_rules": len(rules),
            "objects_tracked": len(set(active_rules.mapped("model_name"))),
            "rules": rules_data,
        }
