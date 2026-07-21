# -*- coding: utf-8 -*-
import uuid

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class UnivApplicantOffer(models.Model):
    _name = "univ.applicant.offer"
    _description = "Admission Offer Letter"
    _inherit = ["mail.thread"]
    _order = "issued_on desc, id desc"

    name = fields.Char(
        string="Offer No",
        copy=False,
        readonly=True,
        default=lambda self: _("New"),
    )
    applicant_id = fields.Many2one(
        comodel_name="univ.applicant",
        string="Applicant",
        required=True,
        ondelete="cascade",
        index=True,
    )
    program_id = fields.Many2one(
        comodel_name="univ.program",
        string="Program",
        related="applicant_id.program_id",
        store=True,
    )
    round_id = fields.Many2one(
        comodel_name="univ.admission.round",
        string="Round",
        related="applicant_id.round_id",
        store=True,
    )
    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("sent", "Sent"),
            ("accepted", "Accepted"),
            ("declined", "Declined"),
            ("expired", "Expired"),
            ("lapsed", "Lapsed"),
        ],
        string="Status",
        default="draft",
        required=True,
        tracking=True,
    )
    issued_on = fields.Datetime(string="Issued On", copy=False)
    accepted_on = fields.Datetime(string="Accepted On", copy=False)
    expiry_date = fields.Date(
        string="Valid Until",
        default=lambda self: fields.Date.add(fields.Date.today(), days=7),
    )
    fee_amount = fields.Monetary(
        string="Admission Fee", currency_field="currency_id"
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        string="Currency",
        default=lambda self: self.env.company.currency_id,
    )
    terms_accepted = fields.Boolean(string="Terms Accepted", copy=False)
    verify_token = fields.Char(
        string="Verification Token", copy=False, index=True, readonly=True
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Campus",
        related="applicant_id.company_id",
        store=True,
        index=True,
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("name") or vals.get("name") in (
                _("New"),
                "New",
            ):
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "univ.applicant.offer"
                ) or "OFFER/0001"
            if not vals.get("verify_token"):
                vals["verify_token"] = uuid.uuid4().hex
        return super().create(vals_list)

    def action_send(self):
        for record in self:
            record.write(
                {"state": "sent", "issued_on": fields.Datetime.now()}
            )
            template = self.env.ref(
                "inom_university_admission.email_template_offer_sent",
                raise_if_not_found=False,
            )
            if template and record.applicant_id.email:
                template.send_mail(record.id, force_send=False)

    def action_accept(self):
        for record in self:
            if record.state not in ("sent", "draft"):
                raise UserError(
                    _("Only a sent offer can be accepted.")
                )
            record.write(
                {
                    "state": "accepted",
                    "accepted_on": fields.Datetime.now(),
                    "terms_accepted": True,
                }
            )

    def action_decline(self):
        self.write({"state": "declined"})

    def action_lapse(self):
        self.write({"state": "lapsed"})

    def action_expire(self):
        self.write({"state": "expired"})

    @api.model
    def _cron_expire_offers(self):
        today = fields.Date.today()
        offers = self.search(
            [
                ("state", "=", "sent"),
                ("expiry_date", "<", today),
            ]
        )
        offers.action_expire()
