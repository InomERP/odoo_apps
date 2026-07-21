# -*- coding: utf-8 -*-
import uuid

from odoo import api, fields, models
from odoo.exceptions import UserError


class UnivApplicant(models.Model):
    _name = "univ.applicant"
    _description = "Admission Applicant"
    _inherit = ["univ.audit.mixin", "mail.thread", "mail.activity.mixin"]
    _order = "applied_date desc, id desc"

    _audit_log_fields = ["stage_id", "offer_state", "fee_state", "student_id"]

    name = fields.Char(string="Applicant Name", required=True, tracking=True)
    application_no = fields.Char(
        string="Application No",
        copy=False,
        readonly=True,
        index=True,
        default=lambda self: self.env._("New"),
    )
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Related Contact",
        ondelete="restrict",
        copy=False,
        index=True,
    )

    # Pipeline
    stage_id = fields.Many2one(
        comodel_name="univ.applicant.stage",
        string="Stage",
        group_expand="_read_group_stage_ids",
        default=lambda self: self._default_stage_id(),
        tracking=True,
        index=True,
        copy=False,
    )
    kanban_state = fields.Selection(
        selection=[
            ("normal", "In Progress"),
            ("blocked", "Blocked"),
            ("done", "Ready"),
        ],
        string="Kanban State",
        default="normal",
    )
    color = fields.Integer(string="Color Index")
    priority = fields.Selection(
        selection=[("0", "Normal"), ("1", "High")],
        string="Priority",
        default="0",
    )

    # Academic placement
    program_id = fields.Many2one(
        comodel_name="univ.program",
        string="Program",
        required=True,
        ondelete="restrict",
        index=True,
        tracking=True,
    )
    round_id = fields.Many2one(
        comodel_name="univ.admission.round",
        string="Admission Round",
        required=True,
        ondelete="restrict",
        index=True,
        tracking=True,
    )
    quota_id = fields.Many2one(
        comodel_name="univ.quota",
        string="Quota",
        ondelete="restrict",
        index=True,
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
    )

    # Personal
    gender = fields.Selection(
        selection=[("male", "Male"), ("female", "Female"), ("other", "Other")],
        string="Gender",
    )
    date_of_birth = fields.Date(string="Date of Birth")
    blood_group = fields.Selection(
        selection=[
            ("a+", "A+"), ("a-", "A-"),
            ("b+", "B+"), ("b-", "B-"),
            ("ab+", "AB+"), ("ab-", "AB-"),
            ("o+", "O+"), ("o-", "O-"),
        ],
        string="Blood Group",
    )
    email = fields.Char(string="Email", tracking=True)
    phone = fields.Char(string="Phone")
    mobile = fields.Char(string="Mobile")
    street = fields.Char(string="Street")
    city = fields.Char(string="City")
    state_id = fields.Many2one(comodel_name="res.country.state", string="State")
    zip = fields.Char(string="ZIP")
    country_id = fields.Many2one(comodel_name="res.country", string="Country")

    applied_date = fields.Date(
        string="Applied On", default=fields.Date.context_today, tracking=True
    )
    source = fields.Selection(
        selection=[
            ("website", "Website"),
            ("walk_in", "Walk-in"),
            ("agent", "Agent / Referral"),
            ("import", "Import"),
            ("other", "Other"),
        ],
        string="Source",
        default="other",
    )
    active = fields.Boolean(string="Active", default=True)
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Campus",
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )

    # Documents
    document_ids = fields.One2many(
        comodel_name="univ.applicant.document",
        inverse_name="applicant_id",
        string="Documents",
    )
    document_count = fields.Integer(
        string="Documents", compute="_compute_document_stats"
    )
    document_progress = fields.Float(
        string="Documents Verified %", compute="_compute_document_stats"
    )
    document_complete = fields.Boolean(
        string="Documents Complete", compute="_compute_document_stats", store=True
    )

    # Merit
    merit_ids = fields.One2many(
        comodel_name="univ.applicant.merit",
        inverse_name="applicant_id",
        string="Merit / Entrance",
    )
    merit_score = fields.Float(
        string="Merit Score", compute="_compute_merit_score", store=True
    )

    # Offer
    offer_ids = fields.One2many(
        comodel_name="univ.applicant.offer",
        inverse_name="applicant_id",
        string="Offers",
    )
    active_offer_id = fields.Many2one(
        comodel_name="univ.applicant.offer",
        string="Current Offer",
        compute="_compute_active_offer",
        store=True,
    )
    offer_state = fields.Selection(
        selection=[
            ("none", "No Offer"),
            ("draft", "Drafted"),
            ("sent", "Sent"),
            ("accepted", "Accepted"),
            ("declined", "Declined"),
            ("expired", "Expired"),
            ("lapsed", "Lapsed"),
        ],
        string="Offer Status",
        compute="_compute_active_offer",
        store=True,
        default="none",
    )

    # Fee (full payment-provider wiring belongs to Phase 3; tracked here)
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        string="Currency",
        default=lambda self: self.env.company.currency_id,
    )
    admission_fee = fields.Monetary(
        string="Admission Fee", currency_field="currency_id"
    )
    fee_state = fields.Selection(
        selection=[
            ("not_required", "Not Required"),
            ("pending", "Pending"),
            ("paid", "Paid"),
            ("lapsed", "Lapsed"),
        ],
        string="Fee Status",
        default="not_required",
        tracking=True,
    )
    fee_paid_date = fields.Date(string="Fee Paid On")

    # Conversion
    student_id = fields.Many2one(
        comodel_name="univ.student",
        string="Enrolled Student",
        readonly=True,
        copy=False,
    )
    is_enrolled = fields.Boolean(
        string="Enrolled", compute="_compute_is_enrolled", store=True
    )
    stage_is_won = fields.Boolean(
        string="Stage Won", related="stage_id.is_won", store=True
    )
    stage_is_rejected = fields.Boolean(
        string="Stage Rejected", related="stage_id.is_rejected", store=True
    )

    reject_reason = fields.Text(string="Rejection / Withdrawal Reason")
    access_token = fields.Char(
        string="Access Token", copy=False, index=True, readonly=True
    )

    # ------------------------------------------------------------------
    # Defaults & stage expansion
    # ------------------------------------------------------------------
    @api.model
    def _default_stage_id(self):
        stage = self.env["univ.applicant.stage"].search(
            [("is_default", "=", True)], limit=1, order="sequence"
        )
        if not stage:
            stage = self.env["univ.applicant.stage"].search(
                [], limit=1, order="sequence"
            )
        return stage.id

    @api.model
    def _read_group_stage_ids(self, stages, domain, order=None):
        program_id = self.env.context.get("default_program_id")
        stage_domain = ["|", ("program_id", "=", False)]
        if program_id:
            stage_domain.append(("program_id", "=", program_id))
        else:
            stage_domain.append(("program_id", "=", False))
        return stages.search(stage_domain, order="sequence")

    def _stage_by_code(self, code):
        stage = self.env["univ.applicant.stage"].search(
            [("code", "=", code), ("program_id", "=", self.program_id.id)],
            limit=1,
        )
        if not stage:
            stage = self.env["univ.applicant.stage"].search(
                [("code", "=", code), ("program_id", "=", False)], limit=1
            )
        return stage

    # ------------------------------------------------------------------
    # Computes
    # ------------------------------------------------------------------
    @api.depends("document_ids", "document_ids.state", "document_ids.mandatory")
    def _compute_document_stats(self):
        for record in self:
            documents = record.document_ids
            record.document_count = len(documents)
            # Completeness is judged on the mandatory set; if none are flagged
            # mandatory, fall back to the full assigned set.
            required = documents.filtered(lambda d: d.mandatory) or documents
            verified_required = required.filtered(lambda d: d.state == "verified")
            record.document_progress = (
                100.0 * len(verified_required) / len(required) if required else 0.0
            )
            record.document_complete = bool(required) and len(
                verified_required
            ) == len(required)

    @api.depends("merit_ids", "merit_ids.weighted_score")
    def _compute_merit_score(self):
        for record in self:
            record.merit_score = sum(record.merit_ids.mapped("weighted_score"))

    @api.depends(
        "offer_ids",
        "offer_ids.state",
        "offer_ids.issued_on",
    )
    def _compute_active_offer(self):
        for record in self:
            offers = record.offer_ids.sorted(
                key=lambda o: (o.issued_on or fields.Datetime.now(), o.id),
                reverse=True,
            )
            active = offers.filtered(
                lambda o: o.state not in ("declined", "expired", "lapsed")
            )[:1]
            current = active or offers[:1]
            record.active_offer_id = current.id if current else False
            record.offer_state = current.state if current else "none"

    @api.depends("stage_id", "stage_id.is_won", "student_id")
    def _compute_is_enrolled(self):
        for record in self:
            record.is_enrolled = bool(record.student_id) or record.stage_id.is_won

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("application_no") or vals.get(
                "application_no"
            ) in (self.env._("New"), "New"):
                vals["application_no"] = self._generate_application_no(vals)
            if not vals.get("access_token"):
                vals["access_token"] = uuid.uuid4().hex
            if not vals.get("partner_id") and vals.get("name"):
                vals["partner_id"] = self._create_partner(vals).id
        applicants = super().create(vals_list)
        # Req 5: generate the course's required documents on new applications.
        applicants._sync_required_documents()
        return applicants

    def write(self, vals):
        res = super().write(vals)
        # Keep the document checklist in sync when the course changes; only
        # ever ADDS missing requirements - never deletes uploaded documents.
        if vals.get("program_id"):
            self._sync_required_documents()
        return res

    # ------------------------------------------------------------------
    # Req 4 / Req 5: course-driven required documents
    # ------------------------------------------------------------------
    def _sync_required_documents(self):
        """Create the documents required by the applicant's course.

        Idempotent and non-destructive: a document is created (in ``draft``)
        only when the applicant does not already have one of that type, so
        uploaded files and the one-document-per-type rule are preserved.
        """
        Document = self.env["univ.applicant.document"]
        for applicant in self:
            requirements = applicant.program_id.document_requirement_ids
            if not requirements:
                continue
            existing_types = set(applicant.document_ids.mapped("doc_type"))
            commands = []
            for requirement in requirements:
                if requirement.doc_type in existing_types:
                    continue
                commands.append({
                    "applicant_id": applicant.id,
                    "doc_type": requirement.doc_type,
                    "mandatory": requirement.mandatory,
                    "state": "draft",
                })
            if commands:
                Document.create(commands)

    @api.onchange("program_id")
    def _onchange_program_id_documents(self):
        """Preview the course's required documents in the form before saving.

        Existing document lines are kept untouched; only the missing required
        types are added as new draft lines so the reviewer sees the full
        checklist immediately.
        """
        for applicant in self:
            requirements = applicant.program_id.document_requirement_ids
            if not requirements:
                continue
            existing_types = set(applicant.document_ids.mapped("doc_type"))
            commands = []
            for requirement in requirements:
                if requirement.doc_type in existing_types:
                    continue
                commands.append((0, 0, {
                    "doc_type": requirement.doc_type,
                    "mandatory": requirement.mandatory,
                    "state": "draft",
                }))
            if commands:
                applicant.document_ids = commands

    def _generate_application_no(self, vals):
        company = (
            self.env["res.company"].browse(vals.get("company_id"))
            if vals.get("company_id")
            else self.env.company
        )
        prefix = company.univ_applicant_prefix or "APP"
        round_prefix = ""
        if vals.get("round_id"):
            admission_round = self.env["univ.admission.round"].browse(
                vals["round_id"]
            )
            round_prefix = (admission_round.sequence_prefix or "").strip()
        sequence = self.env["ir.sequence"].next_by_code(
            "univ.applicant.application"
        ) or "0001"
        parts = [p for p in (prefix, round_prefix, sequence) if p]
        return "/".join(parts)

    def unlink(self):
        if not self.env.user.has_group(
            "inom_university_core.group_univ_admin"
        ):
            enrolled = self.filtered(
                lambda a: a.student_id or a.stage_id.is_won
            )
            if enrolled:
                raise UserError(
                    self.env._(
                        "Enrolled applicants cannot be deleted. Archive them "
                        "instead."
                    )
                )
        return super().unlink()

    def _create_partner(self, vals):
        partner_vals = {
            "name": vals["name"],
            "is_univ_applicant": True,
            "email": vals.get("email"),
            "phone": vals.get("phone"),
            "street": vals.get("street"),
            "city": vals.get("city"),
            "state_id": vals.get("state_id"),
            "zip": vals.get("zip"),
            "country_id": vals.get("country_id"),
            "company_id": vals.get("company_id"),
        }
        return self.env["res.partner"].create(partner_vals)

    # ------------------------------------------------------------------
    # Seat availability
    # ------------------------------------------------------------------
    def _get_seat_cap(self):
        self.ensure_one()
        if not self.quota_id:
            return self.env["univ.quota.seat"]
        return self.env["univ.quota.seat"].search(
            [
                ("program_id", "=", self.program_id.id),
                ("quota_id", "=", self.quota_id.id),
                ("round_id", "=", self.round_id.id),
            ],
            limit=1,
        )

    def _check_seat_available(self):
        self.ensure_one()
        seat = self._get_seat_cap()
        if seat and seat.capacity and seat.available_seats <= 0:
            raise UserError(
                self.env._(
                    "No seats available for quota %(quota)s in %(program)s "
                    "(%(round)s).",
                    quota=self.quota_id.display_name,
                    program=self.program_id.display_name,
                    round=self.round_id.display_name,
                )
            )

    # ------------------------------------------------------------------
    # Pipeline actions
    # ------------------------------------------------------------------
    def action_move_stage(self, code):
        for record in self:
            stage = record._stage_by_code(code)
            if stage:
                record.stage_id = stage.id

    def action_start_verification(self):
        self.action_move_stage("document_verification")

    def action_documents_verified(self):
        for record in self:
            if not record.document_complete:
                raise UserError(
                    self.env._(
                        "All uploaded documents must be verified before moving "
                        "%(name)s to merit evaluation.",
                        name=record.name,
                    )
                )
            record.action_move_stage("merit")

    def action_issue_offer(self):
        self.ensure_one()
        self._check_seat_available()
        offer = self.env["univ.applicant.offer"].create(
            {
                "applicant_id": self.id,
                "fee_amount": self.admission_fee,
            }
        )
        offer.action_send()
        self.action_move_stage("offer")
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Offer"),
            "res_model": "univ.applicant.offer",
            "res_id": offer.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_accept_offer(self):
        self.ensure_one()
        if not self.active_offer_id:
            raise UserError(self.env._("There is no active offer to accept."))
        self.active_offer_id.action_accept()
        if self.admission_fee:
            self.fee_state = "pending"
        else:
            self.fee_state = "not_required"
        self.action_move_stage("fee")
        # No-fee admissions can convert straight away once documents are done.
        self._try_auto_enrol()

    def action_mark_fee_paid(self):
        for record in self:
            if record.offer_state != "accepted":
                raise UserError(
                    self.env._(
                        "The offer must be accepted before recording the "
                        "admission fee."
                    )
                )
            record.fee_state = "paid"
            record.fee_paid_date = fields.Date.context_today(record)
        # Once the fee is settled, convert to a student automatically when the
        # remaining admission gates are already cleared (best-effort, never
        # blocks the fee update if something is still pending).
        self._try_auto_enrol()

    def _try_auto_enrol(self):
        """Automatically enrol applicants whose admission gates are all met.

        Conditions mirror ``_check_can_enrol`` so the subsequent call cannot
        raise: accepted offer, fee paid (or not required), verified documents,
        and no student yet. Applicants not yet ready are simply skipped.
        """
        for record in self:
            if record.student_id:
                continue
            if record.offer_state != "accepted":
                continue
            if record.fee_state not in ("paid", "not_required"):
                continue
            if not record.document_complete:
                continue
            record.action_enrol_to_student()

    def action_reject(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Reject Applicant"),
            "res_model": "univ.applicant.reject.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_applicant_id": self.id},
        }

    def _do_reject(self, reason):
        rejected = self.env["univ.applicant.stage"].search(
            [("is_rejected", "=", True)], limit=1, order="sequence"
        )
        for record in self:
            record.reject_reason = reason
            if rejected:
                record.stage_id = rejected.id
            record.active_offer_id and record.active_offer_id.action_decline()
            record._notify_stage_email("email_template_applicant_rejected")

    def action_reset_pipeline(self):
        self.action_move_stage("application")
        self.write({"reject_reason": False})

    def action_view_student(self):
        self.ensure_one()
        if not self.student_id:
            raise UserError(self.env._("No student record is linked yet."))
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Student"),
            "res_model": "univ.student",
            "res_id": self.student_id.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_assign_required_documents(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Assign Required Documents"),
            "res_model": "univ.assign.documents.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_applicant_id": self.id},
        }

    # ------------------------------------------------------------------
    # One-click conversion
    # ------------------------------------------------------------------
    def _check_can_enrol(self):
        self.ensure_one()
        missing = []
        if self.offer_state != "accepted":
            missing.append(self.env._("an accepted offer"))
        if self.fee_state not in ("paid", "not_required"):
            missing.append(self.env._("admission fee payment"))
        if not self.document_complete:
            missing.append(self.env._("a fully verified document checklist"))
        if self.student_id:
            raise UserError(
                self.env._("Applicant %(name)s is already enrolled.", name=self.name)
            )
        if missing:
            raise UserError(
                self.env._(
                    "Cannot enrol %(name)s yet. Still required: %(items)s.",
                    name=self.name,
                    items=", ".join(missing),
                )
            )

    def _prepare_student_values(self):
        self.ensure_one()
        return {
            "name": self.name,
            "program_id": self.program_id.id,
            "gender": self.gender,
            "category": self.category,
            "date_of_birth": self.date_of_birth,
            "blood_group": self.blood_group,
            "email": self.email,
            "phone": self.phone,
            "mobile": self.mobile,
            "street": self.street,
            "city": self.city,
            "state_id": self.state_id.id,
            "zip": self.zip,
            "country_id": self.country_id.id,
            "company_id": self.company_id.id,
        }

    def _allocate_section(self, student):
        """Pick the first section with free capacity for the program."""
        self.ensure_one()
        sections = self.env["univ.section"].search(
            [("program_id", "=", self.program_id.id)],
            order="id",
        )
        for section in sections:
            if not section.capacity or section.student_count < section.capacity:
                student.section_id = section.id
                if section.batch_id:
                    student.batch_id = section.batch_id.id
                if section.semester_id:
                    student.semester_id = section.semester_id.id
                break

    def action_enrol_to_student(self):
        students = self.env["univ.student"]
        for record in self:
            record._check_can_enrol()
            student = self.env["univ.student"].create(
                record._prepare_student_values()
            )
            record._allocate_section(student)
            record.student_id = student.id
            # Migrate verified documents to the student vault.
            record._copy_documents_to_student(student)
            # Move the applicant to the won (enrolled) stage.
            won = self.env["univ.applicant.stage"].search(
                [("is_won", "=", True)], limit=1, order="sequence"
            )
            if won:
                record.stage_id = won.id
            # Issue portal access and welcome the new student.
            record._grant_portal_access(student)
            record._notify_stage_email("email_template_applicant_welcome")
            students |= student
        if len(students) == 1:
            return {
                "type": "ir.actions.act_window",
                "name": self.env._("Student"),
                "res_model": "univ.student",
                "res_id": students.id,
                "view_mode": "form",
                "target": "current",
            }
        return True

    def _copy_documents_to_student(self, student):
        self.ensure_one()
        mapping = {
            "tenth": "tenth",
            "twelfth": "twelfth",
            "transfer": "transfer",
            "migration": "migration",
            "aadhaar": "id_proof",
            "id_proof": "id_proof",
            "passport": "id_proof",
            "photo": "photo",
            "transcript": "other",
            "visa": "other",
            "entrance": "other",
            "other": "other",
        }
        for doc in self.document_ids:
            # Only carry over documents that were actually uploaded.
            if not doc.file:
                continue
            self.env["univ.student.document"].create(
                {
                    "name": doc.name,
                    "student_id": student.id,
                    "doc_type": mapping.get(doc.doc_type, "other"),
                    "file": doc.file,
                    "file_name": doc.file_name,
                    "state": "verified" if doc.state == "verified" else "pending",
                }
            )

    def _grant_portal_access(self, student):
        self.ensure_one()
        partner = student.partner_id
        if not partner:
            return
        portal_group = self.env.ref("base.group_portal", raise_if_not_found=False)
        if not portal_group:
            return
        existing = self.env["res.users"].sudo().search(
            [("partner_id", "=", partner.id)], limit=1
        )
        if existing or not partner.email:
            return
        self.env["res.users"].sudo().with_context(
            no_reset_password=True
        ).create(
            {
                "name": partner.name,
                "login": partner.email,
                "partner_id": partner.id,
                "groups_id": [(6, 0, [portal_group.id])],
            }
        )

    # ------------------------------------------------------------------
    # Mail helpers
    # ------------------------------------------------------------------
    def _notify_stage_email(self, template_xmlid):
        template = self.env.ref(
            "inom_university_admission.%s" % template_xmlid,
            raise_if_not_found=False,
        )
        for record in self:
            if template and record.email:
                template.send_mail(record.id, force_send=False)

    # ------------------------------------------------------------------
    # Automated maintenance (crons)
    # ------------------------------------------------------------------
    @api.model
    def _cron_auto_reject_stale_documents(self, days=15):
        limit_date = fields.Date.subtract(fields.Date.today(), days=days)
        applicants = self.search(
            [
                ("stage_id.is_won", "=", False),
                ("stage_id.is_rejected", "=", False),
                ("applied_date", "<", limit_date),
                ("document_complete", "=", False),
            ]
        )
        for applicant in applicants:
            applicant.message_post(
                body=self.env._(
                    "Document re-upload window elapsed (%(days)s days). "
                    "Application flagged for review.",
                    days=days,
                )
            )
            applicant.kanban_state = "blocked"

    @api.model
    def _cron_lapse_unpaid_offers(self, days=7):
        limit_dt = fields.Datetime.subtract(fields.Datetime.now(), days=days)
        offers = self.env["univ.applicant.offer"].search(
            [
                ("state", "=", "accepted"),
                ("accepted_on", "<", limit_dt),
                ("applicant_id.fee_state", "=", "pending"),
            ]
        )
        for offer in offers:
            offer.action_lapse()
            offer.applicant_id.fee_state = "lapsed"
            offer.applicant_id._promote_waitlist()

    def _promote_waitlist(self):
        """Promote the next eligible applicant when a seat is freed."""
        self.ensure_one()
        if not self.quota_id:
            return
        candidate = self.search(
            [
                ("program_id", "=", self.program_id.id),
                ("quota_id", "=", self.quota_id.id),
                ("round_id", "=", self.round_id.id),
                ("offer_state", "in", ("none", "draft")),
                ("stage_id.is_rejected", "=", False),
                ("stage_id.is_won", "=", False),
                ("id", "!=", self.id),
            ],
            order="merit_score desc, applied_date asc",
            limit=1,
        )
        if candidate:
            candidate.message_post(
                body=self.env._(
                    "Promoted from waitlist: a seat became available."
                )
            )
            candidate.kanban_state = "done"
