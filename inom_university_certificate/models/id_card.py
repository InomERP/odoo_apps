# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError


class UnivIdCard(models.Model):
    _name = "univ.id.card"
    _description = "Student ID Card"
    _inherit = ["mail.thread"]
    _order = "create_date desc, id desc"

    name = fields.Char(string="Card No.", copy=False, readonly=True,
                       default=lambda self: self.env._("New"))
    student_id = fields.Many2one(comodel_name="univ.student", string="Student",
                                 required=True, index=True)
    program_id = fields.Many2one(comodel_name="univ.program", string="Program",
                                 related="student_id.program_id", store=True)
    photo = fields.Image(string="Photo", related="student_id.image_1920",
                         readonly=False)
    blood_group = fields.Char(string="Blood Group")
    emergency_contact = fields.Char(string="Emergency Contact")
    valid_from = fields.Date(string="Valid From",
                             default=fields.Date.context_today)
    valid_to = fields.Date(string="Valid To")
    verify_url = fields.Char(string="Verification URL",
                             compute="_compute_verify", store=True)
    state = fields.Selection(
        selection=[("draft", "Draft"), ("active", "Active"),
                   ("expired", "Expired"), ("lost", "Lost")],
        string="Status", default="draft", required=True, tracking=True)
    company_id = fields.Many2one(
        comodel_name="res.company", string="Company",
        default=lambda self: self.env.company, index=True)

    @api.depends("name")
    def _compute_verify(self):
        base = self.env["ir.config_parameter"].sudo().get_param("web.base.url")
        for card in self:
            if card.name and card.name not in (self.env._("New"), "New"):
                card.verify_url = "%s/certificate/verify/%s" % (base, card.name)
            else:
                card.verify_url = False

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("name") or vals["name"] in (self.env._("New"), "New"):
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "univ.id.card") or "IDC/0001"
        return super().create(vals_list)

    def action_activate(self):
        self.write({"state": "active"})

    def action_mark_lost(self):
        self.write({"state": "lost"})
