# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class UnivStudent(models.Model):
    _name = "univ.student"
    _description = "Student"
    _inherit = ["univ.audit.mixin", "mail.thread", "mail.activity.mixin"]
    _order = "enrolment_no desc, name"

    # Fields whose changes are written to the immutable audit log.
    _audit_log_fields = [
        "state",
        "program_id",
        "batch_id",
        "section_id",
        "category",
    ]

    name = fields.Char(string="Full Name", required=True, tracking=True)
    enrolment_no = fields.Char(
        string="Enrolment No.",
        readonly=True,
        copy=False,
        index=True,
        tracking=True,
    )
    roll_number = fields.Char(string="Roll Number", copy=False, tracking=True)
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Related Contact",
        ondelete="restrict",
        copy=False,
        tracking=True,
    )
    state = fields.Selection(
        selection=[
            ("draft", "Applicant"),
            ("enrolled", "Enrolled"),
            ("active", "Active"),
            ("graduated", "Graduated"),
            ("dropped", "Dropped"),
        ],
        string="Status",
        default="draft",
        required=True,
        tracking=True,
        copy=False,
    )

    # Academic placement
    program_id = fields.Many2one(
        comodel_name="univ.program",
        string="Program",
        ondelete="restrict",
        index=True,
        tracking=True,
    )
    batch_id = fields.Many2one(
        comodel_name="univ.batch",
        string="Batch",
        ondelete="restrict",
        index=True,
        tracking=True,
    )
    semester_id = fields.Many2one(
        comodel_name="univ.semester",
        string="Current Semester",
        ondelete="set null",
        index=True,
    )
    section_id = fields.Many2one(
        comodel_name="univ.section",
        string="Section",
        ondelete="restrict",
        index=True,
        tracking=True,
    )

    # Personal
    gender = fields.Selection(
        selection=[
            ("male", "Male"),
            ("female", "Female"),
            ("other", "Other"),
        ],
        string="Gender",
        tracking=True,
    )
    category = fields.Selection(
        selection=[
            ("general", "General"),
            ("obc", "OBC"),
            ("sc", "SC"),
            ("st", "ST"),
            ("ews", "EWS"),
            ("other", "Other"),
        ],
        string="Category",
        default="general",
        tracking=True,
    )
    date_of_birth = fields.Date(string="Date of Birth")
    blood_group = fields.Selection(
        selection=[
            ("a+", "A+"),
            ("a-", "A-"),
            ("b+", "B+"),
            ("b-", "B-"),
            ("ab+", "AB+"),
            ("ab-", "AB-"),
            ("o+", "O+"),
            ("o-", "O-"),
        ],
        string="Blood Group",
    )
    medical_notes = fields.Text(string="Medical Notes")
    admission_date = fields.Date(
        string="Admission Date", default=fields.Date.context_today
    )

    # Contact (mirrored onto the partner)
    email = fields.Char(string="Email")
    phone = fields.Char(string="Phone")
    mobile = fields.Char(string="Mobile")
    street = fields.Char(string="Street")
    city = fields.Char(string="City")
    state_id = fields.Many2one(comodel_name="res.country.state", string="State")
    zip = fields.Char(string="ZIP")
    country_id = fields.Many2one(comodel_name="res.country", string="Country")
    image_1920 = fields.Image(string="Photo")

    active = fields.Boolean(string="Active", default=True, tracking=True)
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Campus",
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )

    # Relations
    guardian_ids = fields.One2many(
        comodel_name="univ.student.guardian",
        inverse_name="student_id",
        string="Guardians",
    )
    primary_guardian_id = fields.Many2one(
        comodel_name="univ.student.guardian",
        string="Primary Guardian",
        compute="_compute_primary_guardian",
        store=True,
    )
    document_ids = fields.One2many(
        comodel_name="univ.student.document",
        inverse_name="student_id",
        string="Documents",
    )
    document_count = fields.Integer(
        string="Documents", compute="_compute_document_stats"
    )
    document_complete = fields.Boolean(
        string="Documents Verified", compute="_compute_document_stats", store=True
    )

    @api.depends("guardian_ids.is_primary")
    def _compute_primary_guardian(self):
        for record in self:
            primary = record.guardian_ids.filtered("is_primary")[:1]
            record.primary_guardian_id = primary.id if primary else False

    @api.depends("document_ids", "document_ids.state")
    def _compute_document_stats(self):
        for record in self:
            documents = record.document_ids
            record.document_count = len(documents)
            verified = documents.filtered(lambda d: d.state == "verified")
            record.document_complete = bool(documents) and len(verified) == len(
                documents
            )

    def _sync_partner_values(self, vals):
        """Return the subset of values to mirror onto the related partner."""
        partner_fields = {
            "name": "name",
            "email": "email",
            "phone": "phone",
            "street": "street",
            "city": "city",
            "state_id": "state_id",
            "zip": "zip",
            "country_id": "country_id",
        }
        partner_vals = {}
        for student_field, partner_field in partner_fields.items():
            if student_field in vals:
                partner_vals[partner_field] = vals[student_field]
        return partner_vals

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("enrolment_no"):
                company = (
                    self.env["res.company"].browse(vals.get("company_id"))
                    if vals.get("company_id")
                    else self.env.company
                )
                prefix = company.univ_student_prefix or "STU"
                sequence = self.env["ir.sequence"].next_by_code(
                    "univ.student.enrolment"
                ) or "0001"
                vals["enrolment_no"] = "%s/%s" % (prefix, sequence)
            if not vals.get("partner_id") and vals.get("name"):
                partner_vals = self._sync_partner_values(vals)
                partner_vals.update(
                    {
                        "is_univ_student": True,
                        "company_id": vals.get("company_id"),
                    }
                )
                partner = self.env["res.partner"].create(partner_vals)
                vals["partner_id"] = partner.id
        return super().create(vals_list)

    def write(self, vals):
        result = super().write(vals)
        partner_vals = self._sync_partner_values(vals)
        if partner_vals:
            for record in self:
                if record.partner_id:
                    record.partner_id.write(partner_vals)
        return result

    # --- Lifecycle state machine -------------------------------------------------
    def _check_can_activate(self):
        self.ensure_one()
        missing = []
        if not self.partner_id:
            missing.append(_("related contact"))
        if not self.program_id:
            missing.append(_("program"))
        if not self.batch_id:
            missing.append(_("batch"))
        if not self.section_id:
            missing.append(_("section"))
        if not self.primary_guardian_id:
            missing.append(_("a primary guardian"))
        if not self.document_complete:
            missing.append(_("a verified document checklist"))
        if missing:
            raise UserError(
                _(
                    "Cannot activate student %(name)s. The following are required: "
                    "%(items)s.",
                    name=self.name,
                    items=", ".join(missing),
                )
            )

    def action_enroll(self):
        for record in self:
            if record.state != "draft":
                raise UserError(
                    _("Only applicants can be moved to enrolled.")
                )
            record.state = "enrolled"

    def action_activate(self):
        for record in self:
            if record.state not in ("draft", "enrolled"):
                raise UserError(
                    _("Only applicants or enrolled students can be activated.")
                )
            record._check_can_activate()
            record.state = "active"

    def action_graduate(self):
        for record in self:
            if record.state != "active":
                raise UserError(
                    _("Only active students can be graduated.")
                )
            record.state = "graduated"

    def action_drop(self):
        for record in self:
            if record.state in ("graduated",):
                raise UserError(
                    _("Graduated students cannot be dropped.")
                )
            record.state = "dropped"

    def action_reset_to_draft(self):
        if not self.env.user.has_group(
            "inom_university_core.group_univ_registrar"
        ):
            raise UserError(
                _(
                    "Only the Registrar may reset a student back to applicant."
                )
            )
        self.write({"state": "draft"})
