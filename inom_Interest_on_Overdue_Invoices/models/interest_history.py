# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class InomInterestHistory(models.Model):
    _name = 'inom.interest.history'
    _description = 'Interest History'
    _order = 'calculation_date desc, id desc'

    name = fields.Char(string='Reference', required=True, copy=False,
                       default=lambda self: self.env['ir.sequence'].next_by_code('inom.interest.history'))

    partner_id = fields.Many2one('res.partner', string='Customer', required=True, ondelete='cascade')
    invoice_id = fields.Many2one('account.move', string='Invoice',
                                 domain=[('move_type', '=', 'out_invoice')])
    rule_id = fields.Many2one('overdue.interest.rule', string='Applied Rule')
    calculation_type = fields.Selection([
        ('percentage', 'Percentage'),
        ('flat_fee', 'Flat Fee'),
    ], string='Calculation Type')

    calculation_date = fields.Date(string='Calculation Date', default=fields.Date.today)
    invoice_date = fields.Date(string='Invoice Date', related='invoice_id.invoice_date', store=False)
    due_date = fields.Date(string='Due Date', related='invoice_id.invoice_date_due', store=False)

    days_overdue = fields.Integer(string='Days Overdue')
    days_after_grace = fields.Integer(string='Days After Grace')
    periods_count = fields.Float(string='Periods Count', digits=(16, 4))
    period_type = fields.Char(string='Period Type')

    base_amount = fields.Monetary(string='Principal Amount', currency_field='currency_id')
    calculated_interest = fields.Monetary(string='Calculated Interest', currency_field='currency_id')
    penalty_applied = fields.Monetary(string='Penalty Applied', currency_field='currency_id')
    interest_before_caps = fields.Monetary(string='Interest Before Caps', currency_field='currency_id')
    final_interest = fields.Monetary(string='Final Interest', currency_field='currency_id')
    interest_rate_applied = fields.Float(string='Interest Rate Applied', digits=(16, 4))

    calculation_breakdown = fields.Text(string='Calculation Details')

    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company)

    move_id = fields.Many2one('account.move', string='Journal Entry / Debit Note',
                              copy=False, readonly=True)
    result_type = fields.Char(string='Result Type', compute='_compute_result_type')

    status = fields.Selection([
        ('draft', 'Draft'),
        ('applied', 'Applied'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft')

    @api.depends('move_id')
    def _compute_result_type(self):
        for rec in self:
            if rec.move_id:
                rec.result_type = 'Debit Note' if rec.move_id.move_type == 'out_invoice' else 'Journal Entry'
            else:
                rec.result_type = ''

    @api.model
    def _get_settings(self):
        p = self.env['ir.config_parameter'].sudo()

        def _truthy(key):
            return p.get_param(key) in ('True', 'true', '1', 1, True)

        def _record(model, key):
            rid = int(p.get_param(key, 0) or 0)
            rec = self.env[model].browse(rid) if rid else self.env[model]
            return rec if rec.exists() else self.env[model]

        return {
            'enabled': _truthy('inom_interest.enable_overdue_interest'),
            'auto_compute': _truthy('inom_interest.auto_compute_interest'),
            'auto_apply': _truthy('inom_interest.auto_apply_interest'),
            'output_type': p.get_param('inom_interest.overdue_output_type') or 'debit_note',
            'default_rule': _record('overdue.interest.rule', 'inom_interest.interest_rule_id'),
            'account': _record('account.account', 'inom_interest.interest_account_id'),
            'journal': _record('account.journal', 'inom_interest.interest_journal_id'),
            'product': _record('product.product', 'inom_interest.interest_product_id'),
            'analytic_account': _record('account.analytic.account', 'inom_interest.interest_analytic_account_id'),
        }

    @api.model
    def _resolve_rule(self, partner, default_rule):
        mode = partner.interest_calculation or 'use_default'
        if mode == 'disabled':
            return self.env['overdue.interest.rule']
        if mode == 'enabled':
            return partner.partner_interest_rule_id or default_rule
        return default_rule

    @api.model
    def _get_overdue_invoices(self, partners=None):
        today = fields.Date.context_today(self)
        domain = [
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted'),
            ('payment_state', 'in', ('not_paid', 'partial')),
            ('invoice_date_due', '!=', False),
            ('invoice_date_due', '<', today),
            ('amount_residual', '>', 0.0),
        ]
        if partners is not None:
            domain.append(('partner_id', 'in', partners.ids))
        return self.env['account.move'].search(domain)

    @api.model
    def _evaluate_invoice(self, invoice, settings=None):
        if settings is None:
            settings = self._get_settings()
        if not settings['enabled']:
            return None
        if invoice.move_type != 'out_invoice' or invoice.state != 'posted':
            return None
        if invoice.payment_state not in ('not_paid', 'partial') or invoice.amount_residual <= 0:
            return None
        if not invoice.invoice_date_due:
            return None
        if getattr(invoice, 'inom_interest_exclude', False):
            return None

        partner = invoice.partner_id
        rule = invoice.inom_interest_rule_id or self._resolve_rule(partner, settings['default_rule'])
        if not rule:
            return None

        today = fields.Date.context_today(self)
        grace_days = (rule.grace_days or 0) + (partner.extra_grace_days or 0)
        days_overdue_raw = (today - invoice.invoice_date_due).days
        days_after_grace = days_overdue_raw - grace_days
        if days_after_grace <= 0:
            return None

        base = invoice.amount_residual if rule.calculate_on == 'residual' else invoice.amount_total
        if base <= 0:
            return None

        prior = sum(self.search([
            ('invoice_id', '=', invoice.id),
            ('status', '=', 'applied'),
        ]).mapped('final_interest'))

        period_days = rule.period_days()
        periods = float(days_after_grace) / float(period_days)

        if rule.calculation_type == 'percentage':
            effective_base = base + (prior if rule.compound_interest else 0.0)
            calculated = effective_base * (rule.interest_rate / 100.0) * periods
        else:
            calculated = rule.interest_rate * periods

        penalty = rule.penalty_amount if rule.apply_penalty and rule.penalty_amount > 0 else 0.0
        interest_before_caps = calculated + penalty

        final = interest_before_caps
        if rule.minimum_interest and final < rule.minimum_interest:
            final = rule.minimum_interest
        if rule.maximum_interest and final > rule.maximum_interest:
            final = rule.maximum_interest

        if final <= 0:
            return None

        # Build breakdown text
        breakdown = self._build_breakdown(invoice, rule, today, days_overdue_raw,
                                          grace_days, days_after_grace, periods,
                                          base, calculated, penalty, final)

        return {
            'partner_id': partner.id,
            'invoice_id': invoice.id,
            'rule_id': rule.id,
            'calculation_type': rule.calculation_type,
            'calculation_date': today,
            'days_overdue': days_overdue_raw,
            'days_after_grace': days_after_grace,
            'periods_count': periods,
            'period_type': rule.period_type,
            'base_amount': base,
            'calculated_interest': calculated,
            'penalty_applied': penalty,
            'interest_before_caps': interest_before_caps,
            'final_interest': final,
            'interest_rate_applied': rule.interest_rate,
            'calculation_breakdown': breakdown,
            'currency_id': invoice.currency_id.id,
            'company_id': invoice.company_id.id,
            'status': 'draft',
        }

    @api.model
    def _build_breakdown(self, invoice, rule, today, days_overdue, grace_days,
                         days_after_grace, periods, base, calculated, penalty, final):
        ccy = invoice.currency_id.name
        lines = [
            "Interest Calculation Breakdown",
            "=" * 40,
            f"Invoice: {invoice.name}",
            f"Due Date: {invoice.invoice_date_due}",
            f"Calculation Date: {today}",
            f"",
            f"Rule: {rule.name}",
            f"Calculation Type: {'Flat Fee' if rule.calculation_type == 'flat_fee' else 'Percentage'}",
            f"Period Type: {rule.period_type.capitalize()}",
            f"Interest Rate: {rule.interest_rate} ({'flat' if rule.calculation_type == 'flat_fee' else '%'})",
            f"",
            f"Days Overdue: {days_overdue}",
            f"Grace Period: {grace_days} days",
            f"Interest Days: {days_after_grace}",
            f"Periods: {periods:.4f}",
            f"",
            f"Principal Amount: {ccy} {base:,.2f}",
        ]
        if rule.calculation_type == 'percentage':
            lines.append(f"Formula: {base:,.2f} × {rule.interest_rate/100} × {periods:.4f} periods = {calculated:,.2f}")
        else:
            lines.append(f"Formula: {rule.interest_rate:.2f} × {periods:.4f} periods = {calculated:,.2f}")

        lines.append(f"Calculated Interest: {ccy} {calculated:,.2f}")
        if penalty:
            lines.append(f"Penalty Applied: {ccy} {penalty:,.2f}")
        lines += [
            "=" * 40,
            f"FINAL INTEREST: {ccy} {final:,.2f}",
        ]
        return "\n".join(lines)

    @api.model
    def _upsert_for_invoice(self, invoice, settings=None):
        vals = self._evaluate_invoice(invoice, settings=settings)
        if not vals:
            return self.browse()
        existing = self.search([
            ('invoice_id', '=', invoice.id),
            ('status', '=', 'draft'),
        ], limit=1)
        if existing:
            existing.write(vals)
            return existing
        return self.create(vals)

    @api.model
    def compute_overdue_interest(self, partners=None):
        settings = self._get_settings()
        if not settings['enabled']:
            return self.browse()
        result = self.browse()
        for inv in self._get_overdue_invoices(partners=partners):
            rec = self._upsert_for_invoice(inv, settings=settings)
            result |= rec
        return result

    def action_apply(self):
        settings = self._get_settings()
        for rec in self:
            if rec.status != 'draft' or rec.final_interest <= 0:
                continue
            if settings['output_type'] == 'journal_entry':
                move = rec._create_journal_entry(settings)
            else:
                move = rec._create_debit_note(settings)
            move.action_post()
            rec.write({'status': 'applied', 'move_id': move.id})
        return True

    def action_cancel(self):
        for rec in self:
            if rec.status == 'applied' and rec.move_id:
                raise UserError(_(
                    "Cannot cancel '%s': already applied. Reverse the entry instead.", rec.name))
            rec.status = 'cancelled'
        return True

    def action_open_move(self):
        self.ensure_one()
        if not self.move_id:
            return False
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': self.move_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def _auto_analytic_for_account(self, account, product=None):
        """Last-resort: if the line's account falls under one or more *mandatory*
        analytic plans, build a valid 100%% distribution automatically by
        choosing one analytic account per mandatory ROOT plan.

        This mirrors Odoo's own validation (analytic_mixin._validate_distribution):
        get_relevant_plans() returns a LIST OF DICTS ({'id', 'applicability', ...}),
        and a plan is satisfied when the distribution sums to 100%% for that root
        plan id. Fully defensive: returns False on any problem so posting is never
        broken further than it already is."""
        try:
            company = self.company_id or self.env.company

            kwargs = {'company_id': company.id, 'business_domain': 'invoice'}
            if account:
                kwargs['account'] = account.id
            if product:
                kwargs['product'] = product.id
            Plan = self.env['account.analytic.plan'].sudo().with_company(company)
            plans = Plan.get_relevant_plans(**kwargs)  # -> list of dicts
            Analytic = self.env['account.analytic.account']
            dist = {}
            for plan in plans:
                if isinstance(plan, dict) and plan.get('applicability') == 'mandatory':
                    acc = Analytic.search([
                        ('root_plan_id', '=', plan['id']),
                        ('company_id', 'in', [company.id, False]),
                    ], limit=1)
                    if acc:
                        dist[str(acc.id)] = 100.0
            return dist or False
        except Exception:
            return False

    def _get_source_analytic_distribution(self, settings=None, account=None, product=None):
        """Return an analytic distribution for the interest line so it can be
        posted when the company enforces a *mandatory* analytic distribution.

        Resolution order:
          0) Interest Analytic Account configured in Settings (100%),
          1) distribution already on the original invoice's product lines,
          2) Odoo's analytic distribution model lookup,
          3) auto-pick one account per mandatory plan for this account.
        """
        self.ensure_one()
        if settings is None:
            try:
                settings = self._get_settings()
            except Exception:
                settings = {}
        # 0) explicit configured analytic account
        acc = settings.get('analytic_account') if settings else False
        if acc:
            return {str(acc.id): 100.0}
        # 1) reuse the source invoice's distribution
        if self.invoice_id:
            for ln in self.invoice_id.invoice_line_ids:
                if (ln.display_type in (False, 'product')) and ln.analytic_distribution:
                    return dict(ln.analytic_distribution)
        # 2) Odoo distribution model
        try:
            company = self.company_id or self.env.company
            dist = self.env['account.analytic.distribution.model']._get_distribution({
                'partner_id': self.partner_id.id,
                'partner_category_id': self.partner_id.category_id.ids,
                'company_id': company.id,
            })
            if dist:
                return dist
        except Exception:
            pass
        # 3) auto-pick from mandatory plans (guarantees a valid 100% dist)
        return self._auto_analytic_for_account(account, product)

    def _create_journal_entry(self, settings):
        self.ensure_one()

        company = self.company_id or self.env.company

        # General Journal Required
        journal = settings['journal']
        if not journal or journal.type != 'general':
            journal = self.env['account.journal'].search(
                [('type', '=', 'general'), ('company_id', '=', company.id)],
                limit=1
            )

        if not journal:
            raise UserError(_("Please configure a Miscellaneous (general) journal for interest journal entries."))

        income = settings['account']

        if not income:
            raise UserError(_("Please configure an Interest Income Account in Settings."))

        receivable = self.partner_id.with_company(company).property_account_receivable_id

        if not receivable:
            raise UserError(_("Customer '%s' has no Receivable account.", self.partner_id.display_name))

        inv_ccy = self.currency_id or company.currency_id
        date = self.calculation_date or fields.Date.context_today(self)

        # Convert invoice currency → company currency
        amount = inv_ccy._convert(
            self.final_interest,
            company.currency_id,
            company,
            date
        )

        label = _("Overdue interest - %s", self.invoice_id.name or self.partner_id.display_name)

        analytic = self._get_source_analytic_distribution(
            settings,
            account=income
        )

        return self.env['account.move'].create({
            'move_type': 'entry',
            'journal_id': journal.id,
            'date': date,
            'ref': _("Overdue interest %s", self.name),

            # IMPORTANT FOR MULTI CURRENCY
            'currency_id': inv_ccy.id,

            'line_ids': [

                # Receivable Line
                (0, 0, {
                    'name': label,
                    'partner_id': self.partner_id.id,
                    'account_id': receivable.id,

                    'debit': amount,
                    'credit': 0.0,

                    'currency_id': inv_ccy.id,
                    'amount_currency': self.final_interest,
                }),

                # Income Line
                (0, 0, {
                    'name': label,
                    'partner_id': self.partner_id.id,
                    'account_id': income.id,

                    'debit': 0.0,
                    'credit': amount,

                    'currency_id': inv_ccy.id,
                    'amount_currency': -self.final_interest,

                    'analytic_distribution': analytic if analytic else {},
                }),
            ],
        })

    def _create_debit_note(self, settings):
        self.ensure_one()
        company = self.company_id or self.env.company
        income = settings['account']
        product = settings['product']
        journal = settings['journal']
        if journal and journal.type != 'sale':
            journal = self.env['account.journal']
        if not journal:
            journal = self.env['account.journal'].search(
                [('type', '=', 'sale'), ('company_id', '=', company.id)], limit=1)
        if not journal:
            raise UserError(_("No Sales journal available for interest debit note."))
        line = {
            'name': _("Interest on Overdue Invoice %s", self.invoice_id.name or self.partner_id.display_name),
            'quantity': 1.0,
            'price_unit': self.final_interest,
            'tax_ids': [(6, 0, [])],
        }
        if product:
            line['product_id'] = product.id
        if income:
            line['account_id'] = income.id
        analytic = self._get_source_analytic_distribution(settings, account=income, product=product)
        if analytic:
            line['analytic_distribution'] = analytic
        return self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_id.id,
            'invoice_date': self.calculation_date or fields.Date.context_today(self),
            'journal_id': journal.id,
            'currency_id': (self.currency_id or company.currency_id).id,
            'company_id': company.id,
            'invoice_origin': self.invoice_id.name or self.name,
            'ref': _("Interest on Overdue Invoice %s", self.invoice_id.name),
            'invoice_line_ids': [(0, 0, line)],
        })

    @api.model
    def _cron_compute_overdue_interest(self):
        settings = self._get_settings()
        if not settings['enabled'] or not settings['auto_compute']:
            return
        drafts = self.compute_overdue_interest()
        if settings['auto_apply'] and drafts:
            drafts.action_apply()