# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError


class UnivAuditLog(models.Model):
    """Immutable audit trail for sensitive writes.

    Records are append-only: only members of the University Administrator
    group may delete them, and nobody may edit them once written.
    """

    _name = "univ.audit.log"
    _description = "University Audit Log"
    _order = "log_date desc, id desc"
    _rec_name = "res_name"

    res_model = fields.Char(string="Model", required=True, index=True, readonly=True)
    res_id = fields.Integer(string="Record ID", index=True, readonly=True)
    res_name = fields.Char(string="Record", readonly=True)
    field_name = fields.Char(string="Field", readonly=True)
    field_label = fields.Char(string="Field Label", readonly=True)
    old_value = fields.Text(string="Old Value", readonly=True)
    new_value = fields.Text(string="New Value", readonly=True)
    operation = fields.Selection(
        selection=[
            ("create", "Create"),
            ("write", "Update"),
            ("unlink", "Delete"),
        ],
        string="Operation",
        required=True,
        readonly=True,
    )
    user_id = fields.Many2one(
        comodel_name="res.users",
        string="User",
        required=True,
        readonly=True,
        default=lambda self: self.env.user,
    )
    log_date = fields.Datetime(
        string="Logged On",
        required=True,
        readonly=True,
        default=fields.Datetime.now,
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        readonly=True,
        default=lambda self: self.env.company,
    )

    def write(self, vals):
        """Audit log entries are immutable once created."""
        raise UserError(self.env._("Audit log entries cannot be modified."))

    def unlink(self):
        if not self.env.user.has_group("inom_university_core.group_univ_admin"):
            raise UserError(
                self.env._(
                    "Only a University Administrator may delete audit log entries."
                )
            )
        return super().unlink()
