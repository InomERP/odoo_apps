# -*- coding: utf-8 -*-
# Phase 4 - Fee Deposit Gate.
#
# When an applicant accepts an admission offer, a deposit invoice (a normal
# posted customer account.move, exactly like every other fee invoice in the
# system) is auto-generated for a configurable percentage of the program's
# tuition. Enrolment is then blocked until that invoice is fully paid through
# the existing portal payment flow.
#
# Everything here is additive: new fields + super()-extended hooks on
# univ.applicant. No Phase 1/2/3 method body is rewritten.
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class UnivApplicant(models.Model):
    _inherit = "univ.applicant"

    # ------------------------------------------------------------------
    # Deposit fields (the invoice is a native account.move)
    # ------------------------------------------------------------------
    deposit_required = fields.Boolean(
        string="Deposit Required",
        default=False,
        copy=False,
        help="Set once a deposit invoice has been generated; while True, "
        "enrolment is gated on the deposit being fully paid.",
    )
    deposit_move_id = fields.Many2one(
        comodel_name="account.move",
        string="Deposit Invoice",
        copy=False,
        ondelete="set null",
        index=True,
    )
    deposit_structure_id = fields.Many2one(
        comodel_name="univ.fee.structure",
        string="Deposit Fee Structure",
        copy=False,
    )
    deposit_amount = fields.Monetary(
        string="Deposit Amount",
        currency_field="currency_id",
        copy=False,
    )
    deposit_state = fields.Selection(
        selection=[
            ("not_generated", "Not Generated"),
            ("pending", "Pending"),
            ("partial", "Partially Paid"),
            ("paid", "Paid"),
        ],
        string="Deposit Status",
        compute="_compute_deposit_state",
        store=True,
        default="not_generated",
    )

    @api.depends(
        "deposit_move_id",
        "deposit_move_id.state",
        "deposit_move_id.payment_state",
    )
    def _compute_deposit_state(self):
        for applicant in self:
            move = applicant.deposit_move_id
            if not move or move.state == "cancel":
                applicant.deposit_state = "not_generated"
            elif move.payment_state in ("paid", "in_payment", "reversed"):
                applicant.deposit_state = "paid"
            elif move.payment_state == "partial":
                applicant.deposit_state = "partial"
            else:
                applicant.deposit_state = "pending"

    # ------------------------------------------------------------------
    # Resolving tuition & journal (reuses the existing fee config)
    # ------------------------------------------------------------------
    def _find_deposit_structure(self):
        """Best confirmed fee structure for this applicant's program. Prefers a
        program-wide (no batch/semester) structure matching the applicant's
        category, picking the largest total as the tuition base."""
        self.ensure_one()
        Structure = self.env["univ.fee.structure"]
        if not self.program_id:
            return Structure
        domain = [
            ("program_id", "=", self.program_id.id),
            ("state", "=", "confirmed"),
            "|",
            ("category", "=", "all"),
            ("category", "=", self.category or "all"),
        ]
        structures = Structure.search(domain)
        if not structures:
            return Structure
        structures = structures.sorted(
            key=lambda s: (
                bool(s.semester_id),
                bool(s.batch_id),
                -(s.amount_total or 0.0),
            )
        )
        return structures[:1]

    def _deposit_journal(self):
        self.ensure_one()
        company = self.company_id or self.env.company
        journal = company.fee_journal_id
        if not journal:
            journal = self.env["account.journal"].search(
                [("type", "=", "sale"), ("company_id", "=", company.id)],
                limit=1,
            )
        return journal

    # ------------------------------------------------------------------
    # Deposit invoice generation (idempotent)
    # ------------------------------------------------------------------
    def _ensure_deposit_invoice(self, raise_on_error=False):
        """Create (or reuse) the single active deposit invoice for this
        applicant. Returns the account.move recordset (empty if not applicable).

        Duplicate prevention: if deposit_move_id already points at a
        non-cancelled move, it is returned untouched.
        """
        self.ensure_one()
        Move = self.env["account.move"]

        # Reuse an existing, non-cancelled deposit invoice.
        if self.deposit_move_id and self.deposit_move_id.state != "cancel":
            return self.deposit_move_id

        def _stop(message):
            if raise_on_error:
                raise UserError(message)
            _logger.info(
                "Deposit not generated for %s: %s", self.display_name, message
            )
            return Move

        structure = self._find_deposit_structure()
        if not structure:
            return _stop(
                _(
                    "No confirmed fee structure found for program %(prog)s, "
                    "so the tuition (and deposit) amount cannot be determined.",
                    prog=self.program_id.display_name or "",
                )
            )
        pct = structure.deposit_percentage or 0.0
        if pct <= 0:
            return _stop(
                _(
                    "No Deposit %% is configured on fee structure %(struct)s.",
                    struct=structure.display_name,
                )
            )
        if not self.partner_id:
            return _stop(
                _("Applicant %s has no linked contact.", self.name)
            )
        # Admission deposit covers ONLY the fee heads flagged 'Collect at
        # Admission', each charged at the structure's Deposit %. Any discount
        # on the line is preserved. Remaining heads stay payable later through
        # the normal fee collection process.
        pct_label = int(pct) if float(pct).is_integer() else pct
        line_commands = []
        for line in structure.line_ids.filtered("collect_at_admission"):
            head = line.head_id
            account = head._get_income_account() if head else False
            if not account or line.amount <= 0:
                continue
            vals = {
                "name": _(
                    "%(head)s (Admission Deposit %(pct)s%%)",
                    head=head.name,
                    pct=pct_label,
                ),
                "product_id": head.product_id.id,
                "quantity": 1.0,
                "price_unit": line.amount * pct / 100.0,
                "discount": line.discount_percent or 0.0,
                "account_id": account.id,
            }
            if head.tax_ids:
                vals["tax_ids"] = [(6, 0, head.tax_ids.ids)]
            line_commands.append((0, 0, vals))
        if not line_commands:
            return _stop(
                _(
                    "No fee heads on %(struct)s are marked 'Collect at "
                    "Admission' with a configured income account.",
                    struct=structure.display_name,
                )
            )
        journal = self._deposit_journal()
        if not journal:
            return _stop(
                _(
                    "No sales journal is configured for %s.",
                    (self.company_id or self.env.company).display_name,
                )
            )

        today = fields.Date.context_today(self)
        try:
            move = Move.sudo().create(
                {
                    "move_type": "out_invoice",
                    "partner_id": self.partner_id.id,
                    "invoice_date": today,
                    "invoice_date_due": today,
                    "journal_id": journal.id,
                    "company_id": (self.company_id or self.env.company).id,
                    "invoice_origin": self.application_no or self.name,
                    "is_univ_deposit": True,
                    "univ_deposit_applicant_id": self.id,
                    "invoice_line_ids": line_commands,
                }
            )
            move.action_post()
        except Exception as exc:  # noqa: BLE001 - must not break offer acceptance
            if raise_on_error:
                raise
            _logger.warning(
                "Deposit invoice generation failed for %s: %s",
                self.display_name,
                exc,
            )
            return Move
        self.write(
            {
                "deposit_move_id": move.id,
                "deposit_structure_id": structure.id,
                "deposit_amount": move.amount_total,
                "deposit_required": True,
            }
        )
        self.message_post(
            body=_(
                "Fee invoice %(ref)s generated (%(amt)s) with the full "
                "fee-head breakup.",
                ref=move.name,
                amt=move.amount_total,
            )
        )
        return move

    # ------------------------------------------------------------------
    # Portal: read-only fee structure summary (informational)
    # ------------------------------------------------------------------
    def _portal_fee_summary(self):
        """Semester-grouped fee breakdown for the admission portal.

        Pure read-only helper for display only: it does not create invoices,
        change the deposit, or affect any workflow. Returns a plain dict so the
        QWeb template stays simple.
        """
        self.ensure_one()
        Structure = self.env["univ.fee.structure"]
        summary = {
            "semesters": [],
            "total_gross": 0.0,
            "total_discount": 0.0,
            "total_net": 0.0,
            "currency": self.currency_id,
        }
        if not self.program_id:
            return summary
        structures = Structure.sudo().search([
            ("program_id", "=", self.program_id.id),
            ("state", "=", "confirmed"),
            "|",
            ("category", "=", "all"),
            ("category", "=", self.category or "all"),
        ])
        if not structures:
            return summary

        # One representative structure per semester (prefer a batch-agnostic
        # one, then the richer/larger structure) to avoid double counting.
        chosen = {}
        for structure in structures:
            key = structure.semester_id.id or 0
            current = chosen.get(key)
            if current is None:
                chosen[key] = structure
                continue
            better = (
                (not structure.batch_id and current.batch_id)
                or (structure.amount_total or 0.0) > (current.amount_total or 0.0)
            )
            if better:
                chosen[key] = structure

        ordered = sorted(
            chosen.values(),
            key=lambda s: (
                s.semester_id.sequence if s.semester_id else 0,
                s.semester_id.id or 0,
                s.id,
            ),
        )
        for structure in ordered:
            lines = [{
                "head": line.head_id.name,
                "amount": line.amount,
                "discount": line.discount_amount,
                "net": line.net_amount,
            } for line in structure.line_ids]
            summary["semesters"].append({
                "name": (
                    structure.semester_id.display_name
                    if structure.semester_id else (structure.name or "Programme")
                ),
                "lines": lines,
                "gross": structure.amount_gross,
                "discount": structure.discount_total,
                "net": structure.amount_total,
            })
            summary["total_gross"] += structure.amount_gross
            summary["total_discount"] += structure.discount_total
            summary["total_net"] += structure.amount_total
        return summary

    # ------------------------------------------------------------------
    # Backend actions
    # ------------------------------------------------------------------
    def action_generate_deposit_invoice(self):
        self.ensure_one()
        move = self._ensure_deposit_invoice(raise_on_error=True)
        if not move:
            return False
        return self.action_view_deposit_invoice()

    def action_view_deposit_invoice(self):
        self.ensure_one()
        if not self.deposit_move_id:
            raise UserError(_("No deposit invoice has been generated."))
        return {
            "type": "ir.actions.act_window",
            "name": _("Deposit Invoice"),
            "res_model": "account.move",
            "res_id": self.deposit_move_id.id,
            "view_mode": "form",
            "target": "current",
        }

    # ------------------------------------------------------------------
    # Hook: generate the deposit when the offer is accepted
    # ------------------------------------------------------------------
    def action_accept_offer(self):
        # Generate the deposit BEFORE the Phase 2 accept flow runs its auto-enrol
        # attempt, so the enrolment gate already sees an unpaid deposit.
        for applicant in self:
            if applicant.active_offer_id:
                applicant._ensure_deposit_invoice(raise_on_error=False)
        return super().action_accept_offer()

    # ------------------------------------------------------------------
    # Enrolment gate
    # ------------------------------------------------------------------
    def _check_can_enrol(self):
        res = super()._check_can_enrol()
        if self.deposit_required and self.deposit_state != "paid":
            raise UserError(
                _(
                    "Enrollment is blocked until the admission deposit is "
                    "fully paid."
                )
            )
        return res

    def _try_auto_enrol(self):
        # Never auto-convert an applicant whose required deposit is unpaid; this
        # also stops the Phase 2 auto-enrol path from raising the gate error.
        ready = self.filtered(
            lambda r: not (r.deposit_required and r.deposit_state != "paid")
        )
        return super(UnivApplicant, ready)._try_auto_enrol()
