# -*- coding: utf-8 -*-
from odoo import fields, models


class UnivHostelComplaint(models.Model):
    _name = "univ.hostel.complaint"
    _description = "Hostel Complaint"
    _inherit = ["mail.thread"]
    _order = "create_date desc, id desc"

    name = fields.Char(string="Subject", required=True)
    student_id = fields.Many2one(comodel_name="univ.student", string="Student",
                                 required=True, index=True)
    hostel_id = fields.Many2one(comodel_name="univ.hostel", string="Hostel",
                                index=True)
    category = fields.Selection(
        selection=[("maintenance", "Maintenance"), ("mess", "Mess"),
                   ("cleanliness", "Cleanliness"), ("security", "Security"),
                   ("other", "Other")],
        string="Category", default="maintenance", required=True)
    description = fields.Text(string="Description")
    priority = fields.Selection(
        selection=[("0", "Low"), ("1", "Medium"), ("2", "High")],
        string="Priority", default="0")
    state = fields.Selection(
        selection=[("new", "New"), ("in_progress", "In Progress"),
                   ("resolved", "Resolved"), ("closed", "Closed")],
        string="Status", default="new", required=True, tracking=True)
    company_id = fields.Many2one(
        comodel_name="res.company", string="Company",
        default=lambda self: self.env.company, index=True)

    def action_progress(self):
        self.write({"state": "in_progress"})

    def action_resolve(self):
        self.write({"state": "resolved"})

    def action_close(self):
        self.write({"state": "closed"})


class UnivHostelVisitor(models.Model):
    _name = "univ.hostel.visitor"
    _description = "Hostel Visitor Log"
    _order = "check_in desc, id desc"

    name = fields.Char(string="Visitor Name", required=True)
    student_id = fields.Many2one(comodel_name="univ.student", string="Meeting",
                                 required=True, index=True)
    hostel_id = fields.Many2one(comodel_name="univ.hostel", string="Hostel")
    relation = fields.Char(string="Relation")
    phone = fields.Char(string="Phone")
    check_in = fields.Datetime(string="Check-in",
                               default=fields.Datetime.now)
    check_out = fields.Datetime(string="Check-out")
    company_id = fields.Many2one(
        comodel_name="res.company", string="Company",
        default=lambda self: self.env.company, index=True)

    def action_check_out(self):
        self.write({"check_out": fields.Datetime.now()})


class UnivHostelAttendance(models.Model):
    _name = "univ.hostel.attendance"
    _description = "Hostel Attendance"
    _order = "date desc, id desc"

    student_id = fields.Many2one(comodel_name="univ.student", string="Student",
                                 required=True, index=True)
    hostel_id = fields.Many2one(comodel_name="univ.hostel", string="Hostel",
                                index=True)
    date = fields.Date(string="Date", required=True,
                       default=fields.Date.context_today, index=True)
    state = fields.Selection(
        selection=[("present", "Present"), ("absent", "Absent"),
                   ("leave", "On Leave")],
        string="Status", default="present", required=True)
    company_id = fields.Many2one(
        comodel_name="res.company", string="Company",
        default=lambda self: self.env.company, index=True)

    _sql_constraints = [
        ("student_date_uniq", "unique(student_id, date)",
         "One attendance record per student per day."),
    ]
