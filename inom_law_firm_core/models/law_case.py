# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class LawCase(models.Model):
    _name = "law.case"
    _description = "Legal Case / Matter"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date_opened desc, id desc"

    def _default_stage_id(self):
        return self.env["law.case.stage"].search([], order="sequence, id", limit=1)

    @api.model
    def _read_group_stage_ids(self, stages, domain, *args):
        return stages.search([], order="sequence, id")

    name = fields.Char(string="Matter Title", required=True, tracking=True)
    case_number = fields.Char(string="Case Number", copy=False, readonly=True, index=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one("res.company", required=True,
                                 default=lambda self: self.env.company)
    branch_id = fields.Many2one("law.branch", string="Branch", tracking=True)
    client_id = fields.Many2one("res.partner", string="Client", required=True,
                                domain="[('is_law_client', '=', True)]", tracking=True)
    case_type_id = fields.Many2one("law.case.type", string="Case Type", tracking=True)
    practice_area_id = fields.Many2one("law.practice.area", string="Practice Area", tracking=True)
    stage_id = fields.Many2one(
        "law.case.stage", string="Stage", tracking=True, ondelete="restrict",
        default=lambda self: self._default_stage_id(),
        group_expand="_read_group_stage_ids",
    )
    tag_ids = fields.Many2many("law.case.tag", string="Tags")
    lawyer_id = fields.Many2one("hr.employee", string="Responsible Lawyer",
                                domain="[('is_lawyer', '=', True)]", tracking=True)
    user_id = fields.Many2one("res.users", string="Responsible User",
                              default=lambda self: self.env.user, tracking=True)
    date_opened = fields.Date(string="Date Opened", default=fields.Date.context_today)
    date_closed = fields.Date(string="Date Closed", readonly=True, copy=False)
    priority = fields.Selection([("0", "Normal"), ("1", "High"), ("2", "Urgent")],
                                string="Priority", default="0")
    color = fields.Integer(string="Color Index")
    description = fields.Html(string="Description")
    opposing_party_name = fields.Char(string="Opposing Party")
    opposing_counsel_name = fields.Char(string="Opposing Counsel")
    closure_ids = fields.One2many("law.case.closure", "case_id", string="Closure Checklists")
    is_closed = fields.Boolean(string="Closed", compute="_compute_is_closed", store=True)

    @api.depends("stage_id", "stage_id.is_closing")
    def _compute_is_closed(self):
        for case in self:
            case.is_closed = bool(case.stage_id.is_closing)

    @api.depends("name", "case_number")
    def _compute_display_name(self):
        for case in self:
            if case.case_number:
                case.display_name = "[%s] %s" % (case.case_number, case.name or "")
            else:
                case.display_name = case.name or _("New Case")

    @api.onchange("case_type_id")
    def _onchange_case_type_id(self):
        if self.case_type_id and self.case_type_id.practice_area_id:
            self.practice_area_id = self.case_type_id.practice_area_id

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("case_number"):
                seq = self.env["ir.sequence"].next_by_code("law.case") or "/"
                branch = (self.env["law.branch"].browse(vals["branch_id"])
                          if vals.get("branch_id") else False)
                vals["case_number"] = ("%s-%s" % (branch.code, seq)
                                       if branch and branch.code else seq)
        return super().create(vals_list)

    def write(self, vals):
        if "stage_id" in vals:
            new_stage = self.env["law.case.stage"].browse(vals["stage_id"])
            if new_stage.is_closing:
                for case in self:
                    if not case.closure_ids.filtered(lambda c: c.state == "confirmed"):
                        raise UserError(_(
                            "Complete the closure checklist (use 'Close Case') before moving "
                            "case %s to a closing stage.") % (case.case_number or case.name))
        return super().write(vals)

    def action_close_case(self):
        self.ensure_one()
        closure = self.closure_ids.filtered(lambda c: c.state == "draft")[:1]
        if not closure:
            closure = self.env["law.case.closure"].create({"case_id": self.id})
        return {
            "type": "ir.actions.act_window",
            "name": _("Case Closure Checklist"),
            "res_model": "law.case.closure",
            "res_id": closure.id,
            "view_mode": "form",
            "target": "new",
        }
