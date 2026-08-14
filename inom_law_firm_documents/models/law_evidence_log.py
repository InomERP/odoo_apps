# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class LawEvidenceLog(models.Model):
    _name = "law.evidence.log"
    _description = "Evidence Chain-of-Custody Log (append-only)"
    _order = "log_date desc, id desc"

    evidence_id = fields.Many2one("law.evidence", required=True, ondelete="restrict")
    action = fields.Selection([
        ("collected", "Collected"), ("transferred", "Transferred"),
        ("examined", "Examined"), ("returned", "Returned"), ("disposed", "Disposed"),
    ], string="Action", required=True, default="transferred")
    from_custodian = fields.Char(string="From")
    to_custodian = fields.Char(string="To")
    log_date = fields.Datetime(string="Date", default=fields.Datetime.now)
    user_id = fields.Many2one("res.users", string="Logged By",
                              default=lambda self: self.env.user)
    note = fields.Char()

    @api.depends("evidence_id.reference", "action", "log_date")
    def _compute_display_name(self):
        action_labels = dict(self._fields['action'].selection)
        for log in self:
            ref = log.evidence_id.reference or _("Evidence")
            action_label = action_labels.get(log.action) or ''
            date_str = log.log_date.strftime('%Y-%m-%d') if log.log_date else ''
            parts = [p for p in (ref, action_label, date_str) if p]
            log.display_name = " | ".join(parts)

    def write(self, vals):
        raise UserError(_("The chain-of-custody log is append-only and cannot be edited."))

    def unlink(self):
        raise UserError(_("The chain-of-custody log is append-only and cannot be deleted."))
