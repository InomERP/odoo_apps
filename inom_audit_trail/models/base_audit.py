# -*- coding: utf-8 -*-
from odoo import api, models

AUDIT_MODELS = ("inom.audit.trail.rule", "inom.audit.trail.log", "inom.audit.trail.log.line")


class Base(models.AbstractModel):
    """Extend every model so create/read/write/unlink can be audited according
    to the active inom.audit.trail.rule records. The work short-circuits very early
    for models that have no rule, so the overhead on normal operations is
    negligible."""

    _inherit = "base"

    def _audit_enabled(self):
        env = self.env
        if not env.registry.ready:
            return False
        if env.context.get("inom_audit_trail_skip"):
            return False
        if self._name in AUDIT_MODELS:
            return False
        if self._transient or self._abstract:
            return False
        return True

    # -- CREATE --
    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        if self._audit_enabled():
            self.env["inom.audit.trail.rule"]._audit_log_simple(
                self._name, "create", records.with_context(inom_audit_trail_skip=True))
        return records

    # -- WRITE --
    def write(self, vals):
        snapshot = None
        enabled = self._audit_enabled()
        if enabled:
            snapshot = self.env["inom.audit.trail.rule"]._audit_snapshot(
                self._name, self.with_context(inom_audit_trail_skip=True), vals)
        res = super().write(vals)
        if enabled and snapshot:
            self.env["inom.audit.trail.rule"]._audit_log_write(
                self._name, self.with_context(inom_audit_trail_skip=True), snapshot)
        return res

    # -- UNLINK --
    def unlink(self):
        if self._audit_enabled():
            recs = self.exists().with_context(inom_audit_trail_skip=True)
            self.env["inom.audit.trail.rule"]._audit_log_simple(
                self._name, "unlink", recs)
        return super().unlink()

    # -- READ (high volume: only fires when a read rule exists for the model) --
    def read(self, fields=None, load="_classic_read"):
        res = super().read(fields=fields, load=load)
        if self._audit_enabled():
            rule_model = self.env["inom.audit.trail.rule"]
            if rule_model._audit_get_rules(self._name, "read"):
                rule_model._audit_log_simple(
                    self._name, "read", self.with_context(inom_audit_trail_skip=True))
        return res
