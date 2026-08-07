# -*- coding: utf-8 -*-
"""Threshold alerting.

Evaluation runs inside the sampling cron, against the row that was just
written. It costs one pass over the active rules -- no extra probes, no extra
queries against the host.

Two properties matter more than the thresholds themselves:

  * **Debounce.** A rule fires only after N consecutive breaching samples. A
    single spike during a backup is not an incident, and an alerting system
    that cannot tell the difference gets muted within a week.
  * **Cooldown.** Once notified, a rule stays quiet for its cooldown window
    even while still breaching. Without this, a two-hour incident sends 24
    identical emails and everyone stops reading them.
"""

import json
import logging
from datetime import timedelta

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)

METRICS = [
    ("cpu_percent", "CPU %"),
    ("memory_percent", "Memory %"),
    ("disk_percent", "Disk %"),
    ("load_1m", "Load average (1m)"),
    ("pg_conn_percent", "DB connections %"),
    ("pg_cache_hit_pct", "DB cache hit %"),
    ("pg_longest_query_s", "Longest running query (s)"),
    ("users_online", "Users online"),
    ("users_recent", "Users active (30 min)"),
    ("cron_late_count", "Late scheduled actions"),
    ("mail_outgoing", "Mail queue depth"),
    ("mail_failed", "Failed emails"),
    ("worker_max_rss", "Largest worker memory (bytes)"),
]

# The rule read is bounded rather than an open `search([])`. Alert rules are
# hand-written configuration -- a real installation has a handful, not a
# thousand -- so this ceiling is a guard against a runaway import loading the
# whole table into a cron worker, not a paging window. Hitting it is logged.
RULE_SCAN_LIMIT = 1000


class ServerHealthRule(models.Model):
    _name = "inom.server.health.rule"
    _description = "Server Health Alert Rule"
    _order = "sequence, id"

    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)

    metric = fields.Selection(METRICS, required=True)
    operator = fields.Selection(
        [(">=", "is at or above"), ("<=", "is at or below")],
        default=">=", required=True)
    threshold = fields.Float(required=True)

    consecutive_breaches = fields.Integer(
        default=3, required=True,
        help="Number of consecutive samples that must breach before the "
             "alert opens. Filters out single spikes.")
    cooldown_minutes = fields.Integer(
        default=60, required=True,
        help="Minimum gap between notifications for this rule while it "
             "remains breached.")
    severity = fields.Selection(
        [("warning", "Warning"), ("danger", "Critical")],
        default="warning", required=True)

    notify_email = fields.Boolean(default=True)
    notify_channel = fields.Boolean(string="Post to Discuss")
    notify_webhook = fields.Boolean(string="Call webhook")

    user_ids = fields.Many2many("res.users", string="Notify users")
    # ondelete is stated rather than inherited. 'set null' is what Odoo
    # already applied silently for this optional link, so behaviour is
    # unchanged: deleting a channel leaves the rule in place with the
    # Discuss notification simply switched off.
    channel_id = fields.Many2one(
        "discuss.channel", string="Discuss channel", ondelete="set null")
    webhook_url = fields.Char()

    breach_streak = fields.Integer(
        string="Breach streak", default=0, copy=False, readonly=True,
        help="Consecutive breaching samples seen so far.")
    last_notified_at = fields.Datetime(readonly=True, copy=False)
    alert_ids = fields.One2many("inom.server.health.alert", "rule_id")
    open_alert_count = fields.Integer(compute="_compute_open_alert_count")

    @api.depends("alert_ids.state")
    def _compute_open_alert_count(self):
        grouped = self.env["inom.server.health.alert"]._read_group(
            [("rule_id", "in", self.ids), ("state", "=", "open")],
            ["rule_id"], ["__count"])
        counts = {rule.id: count for rule, count in grouped}
        for rule in self:
            rule.open_alert_count = counts.get(rule.id, 0)

    # ----- evaluation ----------------------------------------------------

    def _breaches(self, value):
        self.ensure_one()
        if value is None:
            return False
        return (value >= self.threshold if self.operator == ">="
                else value <= self.threshold)

    @api.model
    def _evaluate(self, sample):
        """Called from the sampling cron with the freshly written sample.

        Three phases, so the cost no longer grows with the number of rules:

          1. read   -- one bounded rule query and one query for every open
                       alert, instead of one alert search per rule;
          2. plan   -- `_plan_evaluation` decides what happens for each rule
                       in pure Python and issues no queries at all;
          3. apply  -- `_apply_evaluation` performs grouped writes and a
                       single batched create, then fires the notifications in
                       rule order.

        The per-rule decision logic is unchanged. Debounce, cooldown, the
        one-clean-sample recovery and the order in which notifications go out
        all behave exactly as they did when each rule was handled inline.
        """
        rules = self.search([], limit=RULE_SCAN_LIMIT)
        if not rules:
            return
        if len(rules) >= RULE_SCAN_LIMIT:
            _logger.warning(
                "Server health: alert evaluation stopped at %s rules. "
                "Archive the rules you no longer need so every rule is "
                "evaluated on each sample.", RULE_SCAN_LIMIT)

        now = fields.Datetime.now()
        plan = self._plan_evaluation(rules, self._open_alerts_by_rule(rules),
                                     sample, now)
        self._apply_evaluation(plan, now)

    @api.model
    def _open_alerts_by_rule(self, rules):
        """{rule id: its current open alert} in one query.

        The alert model is ordered `opened_at desc`, so the first row seen
        for a rule is the one a per-rule `search(..., limit=1)` returned.
        """
        alerts = self.env["inom.server.health.alert"].search(
            [("rule_id", "in", rules.ids), ("state", "=", "open")])
        by_rule = {}
        for alert in alerts:
            by_rule.setdefault(alert.rule_id.id, alert)
        return by_rule

    @api.model
    def _plan_evaluation(self, rules, open_alerts, sample, now):
        """Decide everything, write nothing.

        Returns the record ids grouped by the values they need, so the caller
        can apply them in a handful of calls. Rules are independent of one
        another -- an alert belongs to exactly one rule -- so deciding for all
        of them up front gives the same result as deciding one at a time.
        """
        plan = {
            "reset_ids": [],        # streak back to zero
            "notified_ids": [],     # last_notified_at stamped
            "resolved_ids": [],     # alerts closing on this sample
            "streaks": [],          # (rule, new streak value)
            "alert_values": [],     # (alert, last_value, peak_value or None)
            "create_vals": [],      # alerts to open, in rule order
            "notifications": [],    # (kind, key, resolved) in rule order
        }

        for rule in rules:
            value = sample[rule.metric]
            alert = open_alerts.get(rule.id)

            if not rule._breaches(value):
                # One clean sample closes it. Recovery should be fast --
                # nobody wants to wait out another debounce window to learn
                # the incident is over.
                if rule.breach_streak:
                    plan["reset_ids"].append(rule.id)
                if alert:
                    plan["resolved_ids"].append(alert.id)
                    plan["alert_values"].append((alert, value, None))
                    plan["notifications"].append(("open", alert.id, True))
                continue

            streak = rule.breach_streak + 1
            plan["streaks"].append((rule, streak))
            if streak < rule.consecutive_breaches:
                continue

            if alert:
                plan["alert_values"].append((
                    alert, value,
                    max(alert.peak_value, value) if rule.operator == ">="
                    else min(alert.peak_value, value)))
                cooled = (
                    not rule.last_notified_at
                    or rule.last_notified_at + timedelta(
                        minutes=rule.cooldown_minutes) <= now)
                if cooled:
                    plan["notifications"].append(("open", alert.id, False))
                    plan["notified_ids"].append(rule.id)
                continue

            plan["notifications"].append(
                ("new", len(plan["create_vals"]), False))
            plan["create_vals"].append({
                "rule_id": rule.id,
                "node": sample.node,
                "opened_at": now,
                "trigger_value": value,
                "peak_value": value,
                "last_value": value,
            })
            plan["notified_ids"].append(rule.id)

        return plan

    @api.model
    def _apply_evaluation(self, plan, now):
        """Write the plan out, then notify in the original rule order.

        Everything that shares a value goes out as one batched write. What is
        left is genuinely per-record -- a streak counter, a last value, a peak
        -- and those are assigned on the record rather than pushed through
        individual write() calls.

        That assignment is not a shortcut. Setting a stored field on a record
        puts the value in the ORM cache and queues the record for flushing;
        `flush` then groups every queued record by the value it needs and
        issues one UPDATE per distinct value. It is the same grouping the
        previous revision did by hand, performed by the ORM instead, and it
        drops the per-group browse() as well: these are the recordsets
        _evaluate already read.
        """
        alert_model = self.env["inom.server.health.alert"]

        # Shared value sets: one call each, whatever the rule count.
        if plan["reset_ids"]:
            self.browse(plan["reset_ids"]).write({"breach_streak": 0})
        if plan["notified_ids"]:
            self.browse(plan["notified_ids"]).write({"last_notified_at": now})
        if plan["resolved_ids"]:
            alert_model.browse(plan["resolved_ids"]).write({
                "state": "resolved", "resolved_at": now})

        # Per-record values, queued for the same flush as the writes above.
        for rule, streak in plan["streaks"]:
            rule.breach_streak = streak
        for alert, last_value, peak_value in plan["alert_values"]:
            alert.last_value = last_value
            if peak_value is not None:
                alert.peak_value = peak_value

        # One create for every alert opened by this sample.
        created = (alert_model.create(plan["create_vals"])
                   if plan["create_vals"] else alert_model)

        self._notify_plan(plan, created, alert_model)

    @api.model
    def _notify_plan(self, plan, created, alert_model):
        """Fan out notifications in the order the rules were evaluated."""
        if not plan["notifications"]:
            return
        # Browsed together so the notification bodies share one prefetch.
        existing = alert_model.browse([
            key for kind, key, _resolved in plan["notifications"]
            if kind == "open"])
        by_id = {alert.id: alert for alert in existing}
        for kind, key, resolved in plan["notifications"]:
            alert = created[key] if kind == "new" else by_id.get(key)
            if alert:
                alert._notify(resolved=resolved)


class ServerHealthAlert(models.Model):
    _name = "inom.server.health.alert"
    _description = "Server Health Alert"
    _order = "opened_at desc"
    _rec_name = "rule_id"

    rule_id = fields.Many2one(
        "inom.server.health.rule", required=True, ondelete="cascade",
        index=True)
    node = fields.Char(index=True)
    state = fields.Selection(
        [("open", "Open"), ("resolved", "Resolved")],
        default="open", required=True, index=True)
    severity = fields.Selection(related="rule_id.severity", store=True)

    opened_at = fields.Datetime(required=True, index=True)
    resolved_at = fields.Datetime()
    trigger_value = fields.Float()
    peak_value = fields.Float()
    last_value = fields.Float()

    duration_s = fields.Float(
        compute="_compute_duration_s", string="Duration",
        help="How long the alert has been open, in hours.")

    @api.depends("opened_at", "resolved_at", "state")
    def _compute_duration_s(self):
        now = fields.Datetime.now()
        for alert in self:
            end = alert.resolved_at or now
            alert.duration_s = (
                (end - alert.opened_at).total_seconds() / 3600.0
                if alert.opened_at else 0.0)

    def _describe(self, resolved=False):
        self.ensure_one()
        rule = self.rule_id
        label = dict(METRICS).get(rule.metric, rule.metric)
        if resolved:
            return _(
                "Recovered: %(metric)s on %(node)s is back within "
                "threshold (now %(value).1f, limit %(threshold).1f).",
                metric=label, node=self.node or "this server",
                value=self.last_value, threshold=rule.threshold)
        return _(
            "%(metric)s on %(node)s %(operator)s %(threshold).1f — "
            "currently %(value).1f, peak %(peak).1f. Breached for "
            "%(count)s consecutive samples.",
            metric=label, node=self.node or "this server",
            operator=dict(rule._fields["operator"].selection).get(
                rule.operator, rule.operator),
            threshold=rule.threshold, value=self.last_value,
            peak=self.peak_value, count=rule.consecutive_breaches)

    def _notify(self, resolved=False):
        """Fan out to the configured channels.

        Every path is wrapped: a broken webhook or a dead mail server must not
        roll back the sample that triggered it.
        """
        self.ensure_one()
        body = self._describe(resolved=resolved)
        subject = _("[%(sev)s] %(rule)s",
                    sev=("Resolved" if resolved
                         else self.rule_id.severity.upper()),
                    rule=self.rule_id.name)

        if self.rule_id.notify_email and self.rule_id.user_ids:
            try:
                # sudo: the sender is the cron user, which has no mail.mail
                # create right. Nothing user-supplied reaches the record --
                # recipients come from the rule's own user_ids and the body
                # from _describe() -- so this widens no data access.
                self.env["mail.mail"].sudo().create({
                    "subject": subject,
                    "body_html": "<p>%s</p>" % body,
                    "email_to": ",".join(
                        u.email for u in self.rule_id.user_ids if u.email),
                    "auto_delete": True,
                }).send()
            except Exception:
                _logger.exception("Server health: email notification failed")

        if self.rule_id.notify_channel and self.rule_id.channel_id:
            try:
                # sudo: posting an infrastructure alert must not depend on
                # the cron user being a member of the target channel. The
                # channel is chosen by a Server Health Manager on the rule,
                # and only the alert text is posted.
                self.rule_id.channel_id.sudo().message_post(
                    body="**%s** — %s" % (subject, body),
                    message_type="comment",
                    subtype_xmlid="mail.mt_comment")
            except Exception:
                _logger.exception("Server health: Discuss notification failed")

        if self.rule_id.notify_webhook and self.rule_id.webhook_url:
            # Blocking network call inside the cron. Short timeout, and the
            # failure is swallowed -- an unreachable webhook must never wedge
            # the sampling job.
            try:
                import requests
                requests.post(
                    self.rule_id.webhook_url,
                    data=json.dumps({
                        "rule": self.rule_id.name,
                        "metric": self.rule_id.metric,
                        "severity": self.rule_id.severity,
                        "state": "resolved" if resolved else "open",
                        "node": self.node,
                        "value": self.last_value,
                        "threshold": self.rule_id.threshold,
                        "message": body,
                    }),
                    headers={"Content-Type": "application/json"},
                    timeout=5)
            except Exception:
                _logger.exception("Server health: webhook notification failed")
