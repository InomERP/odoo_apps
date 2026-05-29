# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class OverdueInterestRule(models.Model):
    _name = 'overdue.interest.rule'
    _description = 'Overdue Interest Rule'
    _rec_name = 'name'

    name = fields.Char(string='Rule Name', required=True)

    active = fields.Boolean(string='Active', default=True)

    # ── Interest Calculation ──────────────────────────────────────────────────
    calculation_type = fields.Selection([
        ('percentage', 'Percentage'),
        ('flat_fee', 'Flat Fee'),
    ], string='Calculation Type', default='percentage', required=True)

    interest_rate = fields.Float(
        string='Interest Rate',
        digits=(16, 4),
        help='For Percentage: rate in %. For Flat Fee: fixed amount per period.'
    )

    period_type = fields.Selection([
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('yearly', 'Yearly'),
    ], string='Period Type', default='monthly', required=True)

    calculate_on = fields.Selection([
        ('residual', 'Residual Amount'),
        ('total', 'Total Invoice Amount'),
    ], string='Calculate On', default='residual', required=True)

    # ── Grace Period ──────────────────────────────────────────────────────────
    grace_days = fields.Integer(
        string='Grace Period (Days)',
        default=0,
        help='Number of days after due date before interest starts accruing.'
    )

    # ── Penalty Settings ──────────────────────────────────────────────────────
    apply_penalty = fields.Boolean(
        string='Apply Penalty',
        default=False,
        help='Apply a one-time penalty in addition to interest.'
    )

    penalty_amount = fields.Float(
        string='Penalty Amount',
        digits=(16, 2),
        help='Fixed penalty amount applied once when invoice becomes overdue.'
    )

    # ── Interest Caps ─────────────────────────────────────────────────────────
    minimum_interest = fields.Float(
        string='Minimum Interest',
        digits=(16, 2),
        default=0.0,
        help='Minimum interest to charge per period. 0 = no minimum.'
    )

    maximum_interest = fields.Float(
        string='Maximum Interest',
        digits=(16, 2),
        default=0.0,
        help='Maximum interest to charge per period. 0 = no maximum.'
    )

    # ── Advanced ──────────────────────────────────────────────────────────────
    compound_interest = fields.Boolean(
        string='Compound Interest',
        default=False,
        help='If enabled, interest is calculated on the accumulated balance including previous interest.'
    )

    # ── Company ───────────────────────────────────────────────────────────────
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        required=True
    )

    sequence = fields.Integer(string='Sequence', default=10)

    # ── Notes ─────────────────────────────────────────────────────────────────
    note = fields.Text(string='Internal Notes')

    # ══════════════════════════════════════════════════════════════════════════
    #  VALIDATION
    # ══════════════════════════════════════════════════════════════════════════

    @api.constrains('interest_rate')
    def _check_interest_rate(self):
        for rec in self:
            if rec.calculation_type == 'percentage':
                if rec.interest_rate <= 0:
                    raise ValidationError(
                        "Percentage type ke liye Interest Rate 0 se zyada hona chahiye."
                    )
                if rec.interest_rate > 100:
                    raise ValidationError(
                        "Interest Rate 100% se zyada nahi ho sakta."
                    )
            elif rec.calculation_type == 'flat_fee':
                if rec.interest_rate < 0:
                    raise ValidationError(
                        "Flat Fee amount negative nahi ho sakta."
                    )

    @api.constrains('grace_days')
    def _check_grace_days(self):
        for rec in self:
            if rec.grace_days < 0:
                raise ValidationError(
                    "Grace Period (Days) negative nahi ho sakta."
                )

    @api.constrains('penalty_amount')
    def _check_penalty_amount(self):
        for rec in self:
            if rec.apply_penalty and rec.penalty_amount <= 0:
                raise ValidationError(
                    "Penalty apply karne ke liye Penalty Amount 0 se zyada hona chahiye."
                )

    @api.constrains('minimum_interest', 'maximum_interest')
    def _check_interest_caps(self):
        for rec in self:
            if rec.minimum_interest < 0:
                raise ValidationError(
                    "Minimum Interest negative nahi ho sakta. 0 = no minimum."
                )
            if rec.maximum_interest < 0:
                raise ValidationError(
                    "Maximum Interest negative nahi ho sakta. 0 = no maximum."
                )
            if (rec.minimum_interest > 0
                    and rec.maximum_interest > 0
                    and rec.minimum_interest > rec.maximum_interest):
                raise ValidationError(
                    "Minimum Interest, Maximum Interest se zyada nahi ho sakta."
                )

    @api.constrains('name')
    def _check_unique_name(self):
        for rec in self:
            duplicate = self.search([
                ('name', '=', rec.name),
                ('company_id', '=', rec.company_id.id),
                ('id', '!=', rec.id),
            ], limit=1)
            if duplicate:
                raise ValidationError(
                    f"Is company mein '{rec.name}' naam ka rule already exist karta hai."
                )

    # ── onchange helpers ──────────────────────────────────────────────────────

    @api.onchange('calculation_type')
    def _onchange_calculation_type(self):
        """Reset rate and period when type changes."""
        if self.calculation_type == 'flat_fee':
            self.period_type = 'daily'
            self.compound_interest = False
        else:
            self.period_type = 'monthly'

    # ══════════════════════════════════════════════════════════════════════════
    #  CALCULATION ENGINE
    # ══════════════════════════════════════════════════════════════════════════

    # Number of calendar days that make up one "period" for each period type.
    _PERIOD_DAYS = {
        'daily': 1,
        'weekly': 7,
        'monthly': 30,
        'yearly': 365,
    }

    def period_days(self):
        self.ensure_one()
        return self._PERIOD_DAYS.get(self.period_type, 30) or 1

    def compute_interest(self, base_amount, days_overdue, prior_interest=0.0):
        """Return the interest amount for one invoice given this rule.

        :param base_amount:   the residual or total invoice amount (already chosen
                               by the caller according to ``calculate_on``).
        :param days_overdue:  effective overdue days AFTER subtracting grace.
        :param prior_interest: interest already applied for this invoice (used only
                               when ``compound_interest`` is enabled).

        The grace period is applied by the caller (it knows the partner's extra
        grace days). Caps (min/max) and the one-time penalty are applied here.
        """
        self.ensure_one()
        if days_overdue <= 0 or base_amount <= 0:
            return 0.0

        # Compound: accrue on top of previously applied interest.
        base = base_amount + (prior_interest if self.compound_interest else 0.0)

        periods = float(days_overdue) / float(self.period_days())

        if self.calculation_type == 'percentage':
            interest = base * (self.interest_rate / 100.0) * periods
        else:  # flat_fee -> fixed amount per period
            interest = self.interest_rate * periods

        # One-time penalty on top of the accrued interest.
        if self.apply_penalty and self.penalty_amount > 0:
            interest += self.penalty_amount

        # Caps (0 = disabled).
        if self.minimum_interest and interest < self.minimum_interest:
            interest = self.minimum_interest
        if self.maximum_interest and interest > self.maximum_interest:
            interest = self.maximum_interest

        return interest