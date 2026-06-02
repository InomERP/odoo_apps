# -*- coding: utf-8 -*-
from odoo import api, fields, models


class AuditTrailLog(models.Model):
    _name = "inom.audit.trail.log"
    _description = "Audit Trail Log"
    _order = "create_date desc"
    _rec_name = "res_name"

    rule_id = fields.Many2one(
        "inom.audit.trail.rule", string="Rule", ondelete="set null", index=True)
    user_id = fields.Many2one(
        "res.users", string="User", index=True,
        default=lambda self: self.env.uid)
    model_id = fields.Many2one("ir.model", string="Object", index=True, ondelete="cascade")
    model_name = fields.Char(
        related="model_id.model", string="Technical Model", store=True)
    res_id = fields.Integer(string="Record ID")
    res_name = fields.Char(string="Record")
    method = fields.Selection(
        [("create", "Create"), ("read", "Read"),
         ("write", "Update"), ("unlink", "Delete")],
        string="Operation", index=True)
    line_ids = fields.One2many(
        "inom.audit.trail.log.line", "log_id", string="Changes")

    # --- request / session context ---
    ip_address = fields.Char(string="IP Address")
    user_agent = fields.Char(string="User Agent")
    browser = fields.Char(string="Browser / OS")
    location = fields.Char(string="Location")

    def name_get_value(self):
        # convenience for some views
        return [(rec.id, "%s · %s" % (rec.method, rec.res_name or "")) for rec in self]


class AuditTrailLogLine(models.Model):
    _name = "inom.audit.trail.log.line"
    _description = "Audit Trail Log Line"

    log_id = fields.Many2one(
        "inom.audit.trail.log", required=True, ondelete="cascade", index=True)
    field_id = fields.Many2one("ir.model.fields", string="Field", ondelete="set null")
    field_name = fields.Char(string="Technical Field")
    field_description = fields.Char(string="Field")
    old_value = fields.Text(string="Old Value")
    new_value = fields.Text(string="New Value")
