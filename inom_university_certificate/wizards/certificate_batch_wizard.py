# -*- coding: utf-8 -*-
from odoo import _, fields, models


class UnivCertificateBatchWizard(models.TransientModel):
    _name = "univ.certificate.batch.wizard"
    _description = "Batch Certificate / ID Card Generation"

    template_id = fields.Many2one(comodel_name="univ.certificate.template",
                                  string="Template", required=True)
    student_ids = fields.Many2many(comodel_name="univ.student",
                                   string="Students", required=True)
    auto_issue = fields.Boolean(string="Approve & Issue", default=True)

    def action_generate(self):
        self.ensure_one()
        Cert = self.env["univ.certificate"]
        created = Cert
        for student in self.student_ids:
            cert = Cert.create({
                "student_id": student.id,
                "template_id": self.template_id.id,
            })
            if self.auto_issue:
                cert.action_approve()
                cert.action_generate()
                cert.action_issue()
            created |= cert
        return {
            "type": "ir.actions.act_window",
            "name": _("Generated Certificates"),
            "res_model": "univ.certificate",
            "view_mode": "list,form",
            "domain": [("id", "in", created.ids)],
        }
