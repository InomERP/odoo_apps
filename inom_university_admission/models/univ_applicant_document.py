# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError

# Allowed upload mime types and max size (bytes) for portal uploads.
ALLOWED_MIMETYPES = (
    "application/pdf",
    "image/png",
    "image/jpeg",
    "image/jpg",
)
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

# Statuses the applicant may NOT change from the portal.
LOCKED_STATES = ("submitted", "under_review", "verified")
# Statuses in which the applicant may upload / replace a file.
UPLOADABLE_STATES = ("draft", "rejected")

# Document types this module understands. Shared by the requirement
# templates and the assignment wizard.
DOC_TYPE_SELECTION = [
    ("tenth", "10th Marksheet"),
    ("twelfth", "12th Marksheet"),
    ("transfer", "Transfer Certificate"),
    ("migration", "Migration Certificate"),
    ("aadhaar", "Aadhaar Card"),
    ("id_proof", "ID Proof"),
    ("photo", "Photograph"),
    ("passport", "Passport"),
    ("transcript", "Academic Transcript"),
    ("visa", "Visa Document"),
    ("entrance", "Entrance Scorecard"),
    ("other", "Other"),
]


class UnivApplicantDocument(models.Model):
    _name = "univ.applicant.document"
    _description = "Applicant Document"
    _inherit = ["mail.thread"]
    _order = "applicant_id, doc_type"

    name = fields.Char(string="Title")
    applicant_id = fields.Many2one(
        comodel_name="univ.applicant",
        string="Applicant",
        required=True,
        ondelete="cascade",
        index=True,
    )
    doc_type = fields.Selection(
        selection=DOC_TYPE_SELECTION,
        string="Document Type",
        required=True,
    )
    mandatory = fields.Boolean(string="Mandatory", default=True)
    version = fields.Integer(string="Revision", default=1, readonly=True)
    file = fields.Binary(string="File", attachment=True)
    file_name = fields.Char(string="File Name", tracking=True)
    state = fields.Selection(
        selection=[
            ("draft", "Awaiting Upload"),
            ("submitted", "Submitted"),
            ("under_review", "Under Review"),
            ("verified", "Verified"),
            ("rejected", "Rejected"),
        ],
        string="Status",
        default="draft",
        required=True,
        tracking=True,
    )
    reject_reason = fields.Char(string="Rejection Reason", tracking=True)
    verified_by = fields.Many2one(
        comodel_name="res.users", string="Reviewed By", readonly=True
    )
    verified_date = fields.Datetime(string="Reviewed On", readonly=True)
    is_locked = fields.Boolean(
        string="Locked",
        compute="_compute_flags",
        help="A locked document cannot be replaced from the portal.",
    )
    can_upload = fields.Boolean(
        string="Uploadable",
        compute="_compute_flags",
        help="The applicant may upload or replace a file in this status.",
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Campus",
        related="applicant_id.company_id",
        store=True,
        index=True,
    )

    _sql_constraints = [
        (
            "uniq_applicant_doctype",
            "unique(applicant_id, doc_type)",
            "Only one document per type is allowed for each application.",
        ),
    ]

    @api.depends("state")
    def _compute_flags(self):
        for record in self:
            record.is_locked = record.state in LOCKED_STATES
            record.can_upload = record.state in UPLOADABLE_STATES

    @api.model_create_multi
    def create(self, vals_list):
        labels = dict(DOC_TYPE_SELECTION)
        for vals in vals_list:
            if not vals.get("name"):
                vals["name"] = labels.get(vals.get("doc_type"), "Document")
            # A freshly assigned requirement (no file) starts in draft;
            # a record created with a file is treated as submitted.
            if not vals.get("state"):
                vals["state"] = "submitted" if vals.get("file") else "draft"
        return super().create(vals_list)

    # ------------------------------------------------------------------
    # Review actions (admission team)
    # ------------------------------------------------------------------
    def action_start_review(self):
        for record in self:
            if record.state == "submitted":
                record.state = "under_review"

    def action_verify(self):
        for record in self:
            if not record.file:
                raise UserError(
                    _("Cannot verify a document with no file attached.")
                )
            record.write(
                {
                    "state": "verified",
                    "verified_by": self.env.user.id,
                    "verified_date": fields.Datetime.now(),
                    "reject_reason": False,
                }
            )
            record.message_post(body=_("Document verified."))

    def action_reject(self):
        for record in self:
            record.write(
                {
                    "state": "rejected",
                    "verified_by": self.env.user.id,
                    "verified_date": fields.Datetime.now(),
                }
            )
            record.message_post(
                body=_(
                    "Document rejected. Reason: %s",
                    record.reject_reason or _("Not specified"),
                )
            )

    def action_reset(self):
        for record in self:
            record.write(
                {
                    "state": "submitted" if record.file else "draft",
                    "verified_by": False,
                    "verified_date": False,
                    "reject_reason": False,
                }
            )

    # ------------------------------------------------------------------
    # Req 3: in-browser preview (PDF / JPG / JPEG / PNG)
    # ------------------------------------------------------------------
    def action_preview(self):
        """Open the uploaded file inside Odoo in a modal dialog.

        The file is shown in an embedded viewer (browser PDF viewer for PDFs,
        inline image for images). The user stays on the same page, nothing is
        downloaded and no external application is launched.
        """
        self.ensure_one()
        if not self.file:
            raise UserError(
                _("There is no file uploaded to preview yet.")
            )
        return {
            "type": "ir.actions.act_window",
            "name": _("Document Preview"),
            "res_model": "univ.document.preview",
            "view_mode": "form",
            "target": "new",
            "context": {"default_document_id": self.id},
        }

    # ------------------------------------------------------------------
    # Portal upload / replace (in-place, keeps a single record per type)
    # ------------------------------------------------------------------
    def portal_submit(self, file_b64, file_name):
        """Attach a file from the portal against an assigned requirement.

        Handles both the initial upload (draft) and the re-upload after a
        rejection. The record is always updated in place - never duplicated -
        so the one-document-per-type rule is preserved and the history is
        retained in the chatter.
        """
        self.ensure_one()
        if self.state not in UPLOADABLE_STATES:
            raise UserError(
                _(
                    "This document is '%s' and cannot be changed.",
                    dict(self._fields["state"].selection).get(self.state),
                )
            )
        was_rejected = self.state == "rejected"
        previous_reason = self.reject_reason
        vals = {
            "file": file_b64,
            "file_name": file_name,
            "state": "submitted",
            "reject_reason": False,
            "verified_by": False,
            "verified_date": False,
        }
        if was_rejected:
            vals["version"] = (self.version or 1) + 1
        self.write(vals)
        if was_rejected:
            self.message_post(
                body=_(
                    "Document re-uploaded by applicant (revision %(rev)s). "
                    "Previous rejection reason: %(reason)s",
                    rev=self.version,
                    reason=previous_reason or _("Not specified"),
                )
            )
        else:
            self.message_post(body=_("Document submitted by applicant."))
        return self
