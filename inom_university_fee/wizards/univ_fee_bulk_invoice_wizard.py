# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class UnivFeeBulkInvoiceWizard(models.TransientModel):
    _name = "univ.fee.bulk.invoice.wizard"
    _description = "Bulk Fee Invoice Generation"

    structure_id = fields.Many2one(
        comodel_name="univ.fee.structure",
        string="Fee Structure",
        required=True,
        domain="[('state', '=', 'confirmed')]",
    )
    program_id = fields.Many2one(
        comodel_name="univ.program", string="Program",
        related="structure_id.program_id", readonly=True,
    )
    batch_id = fields.Many2one(
        comodel_name="univ.batch", string="Batch",
        help="Restrict to a batch (defaults to the structure batch).",
    )
    semester_id = fields.Many2one(
        comodel_name="univ.semester", string="Semester",
    )
    only_active_students = fields.Boolean(
        string="Active Students Only", default=True
    )
    invoice_date = fields.Date(
        string="Invoice Date", default=fields.Date.context_today, required=True
    )
    due_date = fields.Date(string="Due Date", required=True)
    post_invoices = fields.Boolean(
        string="Post Immediately", default=True,
        help="Validate the generated invoices straight away.",
    )
    student_count = fields.Integer(
        string="Matching Students", compute="_compute_student_count"
    )
    result_summary = fields.Text(string="Result", readonly=True)

    @api.onchange("structure_id")
    def _onchange_structure_id(self):
        if self.structure_id:
            self.batch_id = self.structure_id.batch_id
            self.semester_id = self.structure_id.semester_id

    def _student_domain(self):
        self.ensure_one()
        structure = self.structure_id
        domain = [("program_id", "=", structure.program_id.id)]
        batch = self.batch_id or structure.batch_id
        if batch:
            domain.append(("batch_id", "=", batch.id))
        semester = self.semester_id or structure.semester_id
        if semester:
            domain.append(("semester_id", "=", semester.id))
        if structure.category and structure.category != "all":
            domain.append(("category", "=", structure.category))
        if structure.quota_id:
            domain.append(("fee_quota_id", "=", structure.quota_id.id))
        if self.only_active_students:
            domain.append(("state", "=", "active"))
        return domain

    @api.depends(
        "structure_id", "batch_id", "semester_id", "only_active_students"
    )
    def _compute_student_count(self):
        for wizard in self:
            if wizard.structure_id:
                wizard.student_count = self.env["univ.student"].search_count(
                    wizard._student_domain()
                )
            else:
                wizard.student_count = 0

    def action_generate(self):
        self.ensure_one()
        structure = self.structure_id
        if structure.state != "confirmed":
            raise UserError(
                _("Confirm the fee structure before generating invoices.")
            )
        students = self.env["univ.student"].search(self._student_domain())
        if not students:
            raise UserError(_("No students match the selected filters."))

        FeeInvoice = self.env["univ.fee.invoice"]
        Move = self.env["account.move"]
        created = self.env["univ.fee.invoice"]
        skipped = 0
        for student in students:
            if not student.partner_id:
                skipped += 1
                continue
            # Avoid duplicate invoices for the same student + structure.
            exists = FeeInvoice.search_count(
                [
                    ("student_id", "=", student.id),
                    ("structure_id", "=", structure.id),
                    ("move_state", "!=", "cancel"),
                ]
            )
            if exists:
                skipped += 1
                continue
            wrapper = FeeInvoice.create(
                {
                    "student_id": student.id,
                    "structure_id": structure.id,
                    "company_id": structure.company_id.id,
                }
            )
            move = Move.create(
                {
                    "move_type": "out_invoice",
                    "partner_id": student.partner_id.id,
                    "invoice_date": self.invoice_date,
                    "invoice_date_due": self.due_date,
                    "journal_id": wrapper._get_fee_journal().id,
                    "invoice_origin": structure.name,
                    "invoice_line_ids": FeeInvoice._build_invoice_lines(structure),
                }
            )
            wrapper.move_id = move.id
            if self.post_invoices:
                move.action_post()
            created |= wrapper

        self.result_summary = _(
            "Generated %(count)s invoices (%(skipped)s skipped).",
            count=len(created),
            skipped=skipped,
        )
        return {
            "type": "ir.actions.act_window",
            "name": _("Generated Fee Invoices"),
            "res_model": "univ.fee.invoice",
            "view_mode": "list,form",
            "domain": [("id", "in", created.ids)],
        }
