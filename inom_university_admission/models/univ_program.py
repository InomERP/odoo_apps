# -*- coding: utf-8 -*-
from odoo import api, fields, models

from .univ_applicant_document import DOC_TYPE_SELECTION


class UnivProgram(models.Model):
    """Course-wise required document configuration.

    Each course (program) maintains its own checklist of documents an
    applicant must provide. The list can be typed in directly or seeded from a
    reusable ``univ.document.requirement.template`` without losing existing
    entries.
    """

    _inherit = "univ.program"

    document_requirement_ids = fields.One2many(
        comodel_name="univ.program.document.requirement",
        inverse_name="program_id",
        string="Required Documents",
        copy=True,
    )
    document_requirement_count = fields.Integer(
        string="Required Document Count",
        compute="_compute_document_requirement_count",
    )
    document_template_id = fields.Many2one(
        comodel_name="univ.document.requirement.template",
        string="Document Template",
        help="Optional reusable checklist. Use 'Load Template' to copy its "
             "lines into this course without removing existing entries.",
    )

    @api.depends("document_requirement_ids")
    def _compute_document_requirement_count(self):
        for record in self:
            record.document_requirement_count = len(
                record.document_requirement_ids
            )

    def action_load_document_template(self):
        """Append the selected template's lines, skipping document types that
        are already configured on the course (no duplicates)."""
        for record in self:
            template = record.document_template_id
            if not template:
                continue
            existing = set(record.document_requirement_ids.mapped("doc_type"))
            commands = []
            for line in template.line_ids:
                if line.doc_type in existing:
                    continue
                commands.append((0, 0, {
                    "doc_type": line.doc_type,
                    "mandatory": line.mandatory,
                    "sequence": line.sequence,
                }))
            if commands:
                record.document_requirement_ids = commands
        return True


class UnivProgramDocumentRequirement(models.Model):
    _name = "univ.program.document.requirement"
    _description = "Course Required Document"
    _order = "sequence, id"

    program_id = fields.Many2one(
        comodel_name="univ.program",
        string="Course / Program",
        required=True,
        ondelete="cascade",
        index=True,
    )
    sequence = fields.Integer(string="Sequence", default=10)
    doc_type = fields.Selection(
        selection=DOC_TYPE_SELECTION,
        string="Document Type",
        required=True,
    )
    mandatory = fields.Boolean(string="Mandatory", default=True)
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Campus",
        related="program_id.company_id",
        store=True,
        index=True,
    )

    _sql_constraints = [
        (
            "uniq_program_doctype",
            "unique(program_id, doc_type)",
            "A document type can only be listed once per course.",
        ),
    ]
