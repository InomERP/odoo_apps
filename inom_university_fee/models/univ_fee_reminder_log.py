# -*- coding: utf-8 -*-
from odoo import fields, models


class UnivFeeReminderLog(models.Model):
    _name = "univ.fee.reminder.log"
    _description = "Fee Reminder Log"
    _order = "sent_on desc, id desc"

    invoice_id = fields.Many2one(
        comodel_name="univ.fee.invoice",
        string="Fee Invoice",
        required=True,
        ondelete="cascade",
        index=True,
    )
    student_id = fields.Many2one(
        comodel_name="univ.student", string="Student",
        related="invoice_id.student_id", store=True,
    )
    milestone = fields.Selection(
        selection=[
            ("d7", "D+7"),
            ("d15", "D+15"),
            ("d30", "D+30"),
        ],
        string="Milestone",
        required=True,
    )
    channel = fields.Selection(
        selection=[
            ("email", "Email"),
            ("sms", "SMS"),
            ("activity", "Counsellor Task"),
        ],
        string="Channel",
        required=True,
    )
    sent_on = fields.Datetime(
        string="Sent On", default=fields.Datetime.now, required=True
    )
    company_id = fields.Many2one(
        comodel_name="res.company", string="Company",
        related="invoice_id.company_id", store=True, index=True,
    )

    _sql_constraints = [
        ("invoice_milestone_uniq", "unique(invoice_id, milestone)",
         "A reminder milestone is logged only once per invoice."),
    ]
