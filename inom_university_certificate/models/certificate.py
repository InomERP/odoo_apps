# -*- coding: utf-8 -*-
import hashlib

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from .certificate_template import CERT_TYPES


class UnivCertificate(models.Model):
    _name = "univ.certificate"
    _description = "Certificate"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc, id desc"

    name = fields.Char(string="Number", copy=False, readonly=True,
                       default=lambda self: _("Draft"))
    student_id = fields.Many2one(comodel_name="univ.student", string="Student",
                                 required=True, index=True, tracking=True)
    template_id = fields.Many2one(comodel_name="univ.certificate.template",
                                  string="Template", required=True)
    cert_type = fields.Selection(selection=CERT_TYPES, string="Type",
                                 related="template_id.cert_type", store=True)
    request_date = fields.Date(string="Requested On",
                               default=fields.Date.context_today)
    issue_date = fields.Date(string="Issued On", readonly=True)
    version = fields.Integer(string="Version", default=1, readonly=True)
    superseded_by_id = fields.Many2one(comodel_name="univ.certificate",
                                       string="Superseded By", readonly=True)
    body_html = fields.Html(string="Rendered Body", readonly=True)
    purpose = fields.Char(string="Purpose")
    verify_url = fields.Char(string="Verification URL", compute="_compute_verify",
                             store=True)
    signed_hash = fields.Char(string="Digital Signature (SHA-256)",
                              readonly=True, copy=False)
    state = fields.Selection(
        selection=[
            ("request", "Requested"),
            ("approved", "Approved"),
            ("generated", "Generated"),
            ("issued", "Issued"),
            ("superseded", "Superseded"),
            ("rejected", "Rejected"),
        ], string="Status", default="request", required=True, tracking=True,
        index=True)
    company_id = fields.Many2one(
        comodel_name="res.company", string="Company",
        default=lambda self: self.env.company, index=True)

    _sql_constraints = [
        ("number_uniq", "unique(name, company_id)",
         "Certificate number must be unique."),
    ]

    @api.depends("name")
    def _compute_verify(self):
        base = self.env["ir.config_parameter"].sudo().get_param("web.base.url")
        for cert in self:
            if cert.name and cert.name not in (_("Draft"), "Draft"):
                cert.verify_url = "%s/certificate/verify/%s" % (base, cert.name)
            else:
                cert.verify_url = False

    def _render_body(self):
        self.ensure_one()
        student = self.student_id
        template = self.template_id.body_html or ""
        mapping = {
            "{student}": student.display_name or "",
            "{program}": student.program_id.display_name or "",
            "{batch}": student.batch_id.display_name or "",
            "{date}": fields.Date.to_string(fields.Date.context_today(self)),
            "{number}": self.name or "",
        }
        for key, value in mapping.items():
            template = template.replace(key, value)
        return template

    def action_approve(self):
        for cert in self:
            if cert.state != "request":
                raise UserError(_("Only requested certificates can be approved."))
            cert.state = "approved"

    def action_reject(self):
        self.write({"state": "rejected"})

    def action_generate(self):
        """Assign number, render the body, compute the signature hash, QR."""
        for cert in self:
            if cert.state != "approved":
                raise UserError(_("Approve the certificate first."))
            if not cert.name or cert.name in (_("Draft"), "Draft"):
                seq = self.env["ir.sequence"].next_by_code(
                    "univ.certificate") or "CERT/0001"
                prefix = cert.template_id.prefix or ""
                cert.name = "%s%s" % (prefix, seq)
            cert.body_html = cert._render_body()
            raw = "%s|%s|%s" % (cert.name, cert.student_id.id,
                                cert.body_html or "")
            cert.signed_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()
            cert.state = "generated"

    def action_issue(self):
        for cert in self:
            if cert.state != "generated":
                raise UserError(_("Generate the certificate first."))
            cert.write({"state": "issued",
                        "issue_date": fields.Date.context_today(cert)})

    def action_reissue(self):
        """Create a new version and mark the current one superseded."""
        self.ensure_one()
        if self.state != "issued":
            raise UserError(_("Only issued certificates can be re-issued."))
        new = self.copy({
            "version": self.version + 1,
            "state": "approved",
            "name": _("Draft"),
            "body_html": False,
            "signed_hash": False,
            "issue_date": False,
        })
        new.action_generate()
        new.action_issue()
        self.write({"state": "superseded", "superseded_by_id": new.id})
        return {
            "type": "ir.actions.act_window",
            "res_model": "univ.certificate",
            "res_id": new.id,
            "view_mode": "form",
            "target": "current",
        }
