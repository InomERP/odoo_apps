# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError

from odoo.addons.inom_university_admission.models.univ_applicant_document import (
    DOC_TYPE_SELECTION,
)


class UnivAssignDocumentsWizard(models.TransientModel):
    _name = "univ.assign.documents.wizard"
    _description = "Assign Required Documents"

    applicant_id = fields.Many2one(
        comodel_name="univ.applicant",
        string="Applicant",
        required=True,
    )
    template_id = fields.Many2one(
        comodel_name="univ.document.requirement.template",
        string="Apply Template",
        help="Pick a template to pre-fill the required document list.",
    )
    line_ids = fields.One2many(
        comodel_name="univ.assign.documents.wizard.line",
        inverse_name="wizard_id",
        string="Required Documents",
    )

    @api.onchange("template_id")
    def _onchange_template_id(self):
        if not self.template_id:
            return
        existing_types = set(self.line_ids.mapped("doc_type"))
        new_lines = self.line_ids
        for tline in self.template_id.line_ids:
            if tline.doc_type not in existing_types:
                new_lines += self.env["univ.assign.documents.wizard.line"].new(
                    {"doc_type": tline.doc_type, "mandatory": tline.mandatory}
                )
        self.line_ids = new_lines

    def action_assign(self):
        self.ensure_one()
        if not self.line_ids:
            raise UserError(
                self.env._("Please add at least one required document.")
            )
        Document = self.env["univ.applicant.document"]
        existing_types = set(
            self.applicant_id.document_ids.mapped("doc_type")
        )
        labels = dict(DOC_TYPE_SELECTION)
        created = self.env["univ.applicant.document"]
        skipped = []
        for line in self.line_ids:
            if line.doc_type in existing_types:
                skipped.append(labels.get(line.doc_type, line.doc_type))
                continue
            created |= Document.create(
                {
                    "applicant_id": self.applicant_id.id,
                    "doc_type": line.doc_type,
                    "mandatory": line.mandatory,
                    "state": "draft",
                }
            )
            existing_types.add(line.doc_type)
        if created:
            names = ", ".join(
                labels.get(d, d) for d in created.mapped("doc_type")
            )
            self.applicant_id.message_post(
                body=self.env._("Required documents assigned: %s", names)
            )
            # Phase 2: notify the applicant outbound (e-mail + portal) that
            # documents have been requested. Reuses the existing workflow; the
            # verification process itself is unchanged.
            self.applicant_id._notify_documents_required(created)
        return {"type": "ir.actions.act_window_close"}


class UnivAssignDocumentsWizardLine(models.TransientModel):
    _name = "univ.assign.documents.wizard.line"
    _description = "Assign Required Documents Line"

    wizard_id = fields.Many2one(
        comodel_name="univ.assign.documents.wizard",
        string="Wizard",
        required=True,
        ondelete="cascade",
    )
    doc_type = fields.Selection(
        selection=DOC_TYPE_SELECTION,
        string="Document Type",
        required=True,
    )
    mandatory = fields.Boolean(string="Mandatory", default=True)
