# -*- coding: utf-8 -*-
from odoo import fields, models

from .univ_applicant_document import DOC_TYPE_SELECTION


class UnivDocumentRequirementTemplate(models.Model):
    _name = "univ.document.requirement.template"
    _description = "Document Requirement Template"
    _order = "name"

    name = fields.Char(string="Template", required=True, translate=True)
    description = fields.Text(string="Description")
    active = fields.Boolean(string="Active", default=True)
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Campus",
        default=lambda self: self.env.company,
        index=True,
    )
    line_ids = fields.One2many(
        comodel_name="univ.document.requirement.template.line",
        inverse_name="template_id",
        string="Required Documents",
        copy=True,
    )


class UnivDocumentRequirementTemplateLine(models.Model):
    _name = "univ.document.requirement.template.line"
    _description = "Document Requirement Template Line"
    _order = "sequence, id"

    template_id = fields.Many2one(
        comodel_name="univ.document.requirement.template",
        string="Template",
        required=True,
        ondelete="cascade",
    )
    sequence = fields.Integer(string="Sequence", default=10)
    doc_type = fields.Selection(
        selection=DOC_TYPE_SELECTION,
        string="Document Type",
        required=True,
    )
    mandatory = fields.Boolean(string="Mandatory", default=True)

    _sql_constraints = [
        (
            "uniq_template_doctype",
            "unique(template_id, doc_type)",
            "A document type can only be listed once per template.",
        ),
    ]
