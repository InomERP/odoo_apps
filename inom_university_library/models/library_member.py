# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class UnivLibraryMember(models.Model):
    _name = "univ.library.member"
    _description = "Library Member"
    _inherit = ["mail.thread"]
    _order = "name"

    name = fields.Char(string="Member", compute="_compute_name", store=True)
    code = fields.Char(string="Card No.", copy=False, readonly=True,
                       default=lambda self: _("New"))
    member_type = fields.Selection(
        selection=[("student", "Student"), ("faculty", "Faculty")],
        string="Type", default="student", required=True)
    student_id = fields.Many2one(comodel_name="univ.student", string="Student",
                                 index=True)
    faculty_id = fields.Many2one(comodel_name="univ.faculty", string="Faculty",
                                 index=True)
    partner_id = fields.Many2one(comodel_name="res.partner", string="Contact",
                                 compute="_compute_partner", store=True)
    max_books = fields.Integer(string="Book Limit", default=3)
    valid_to = fields.Date(string="Valid Until")
    issued_count = fields.Integer(string="Currently Issued",
                                  compute="_compute_issued")
    state = fields.Selection(
        selection=[("active", "Active"), ("suspended", "Suspended"),
                   ("expired", "Expired")],
        string="Status", default="active", required=True, tracking=True)
    company_id = fields.Many2one(
        comodel_name="res.company", string="Company",
        default=lambda self: self.env.company, index=True)

    @api.depends("student_id", "faculty_id", "member_type")
    def _compute_name(self):
        for member in self:
            rec = member.student_id if member.member_type == "student" \
                else member.faculty_id
            member.name = rec.display_name if rec else _("Member")

    @api.depends("student_id", "faculty_id", "member_type")
    def _compute_partner(self):
        for member in self:
            if member.member_type == "student":
                member.partner_id = member.student_id.partner_id
            else:
                member.partner_id = member.faculty_id.partner_id

    def _compute_issued(self):
        Issue = self.env["univ.library.issue"]
        for member in self:
            member.issued_count = Issue.search_count([
                ("member_id", "=", member.id), ("state", "in", ("issued", "overdue"))])

    @api.constrains("member_type", "student_id", "faculty_id")
    def _check_member(self):
        for member in self:
            if member.member_type == "student" and not member.student_id:
                raise ValidationError(_("Select the student."))
            if member.member_type == "faculty" and not member.faculty_id:
                raise ValidationError(_("Select the faculty."))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("code") or vals["code"] in (_("New"), "New"):
                vals["code"] = self.env["ir.sequence"].next_by_code(
                    "univ.library.member") or "LIB-M/0001"
        return super().create(vals_list)

    def action_suspend(self):
        self.write({"state": "suspended"})

    def action_activate(self):
        self.write({"state": "active"})
