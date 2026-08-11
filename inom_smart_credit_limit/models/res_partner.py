# -*- coding: utf-8 -*-
# Part of INOM Smart Credit Limit. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from datetime import timedelta

from odoo import api, fields, models, _


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # ------------------------------------------------------------------
    # Configuration fields
    # ------------------------------------------------------------------
    use_smart_credit = fields.Boolean(
        string="Smart Credit Control",
        tracking=True,
        help="Enable INOM Smart Credit control for this customer.")
    smart_credit_limit = fields.Monetary(
        string="Smart Credit Limit",
        currency_field='currency_id',
        tracking=True,
        help="Maximum credit exposure allowed for this customer "
             "(open receivables + uninvoiced confirmed orders).")
    credit_enforcement = fields.Selection(
        selection=[
            ('follow', 'Follow Global Policy'),
            ('warn', 'Warn Only'),
            ('block', 'Block'),
        ],
        string="Enforcement Mode",
        default='follow',
        tracking=True,
        help="Per-customer override of the global checkpoint policy "
             "applied when the credit limit is exceeded.")

    # ------------------------------------------------------------------
    # Live exposure fields (computed, not stored)
    # ------------------------------------------------------------------
    smart_credit_exposure = fields.Monetary(
        string="Credit Exposure",
        compute='_compute_smart_credit_amounts',
        currency_field='currency_id',
        help="Open posted receivables plus uninvoiced amount of "
             "confirmed sale orders (whole commercial entity).")
    smart_extra_credit = fields.Monetary(
        string="Active Extensions",
        compute='_compute_smart_credit_amounts',
        currency_field='currency_id',
        help="Sum of currently active temporary credit extensions.")
    smart_available_credit = fields.Monetary(
        string="Available Credit",
        compute='_compute_smart_credit_amounts',
        currency_field='currency_id')
    smart_credit_utilization = fields.Float(
        string="Utilization (%)",
        compute='_compute_smart_credit_amounts',
        help="Credit exposure as a percentage of the effective limit.")

    # ------------------------------------------------------------------
    # Smart scoring
    # ------------------------------------------------------------------
    smart_credit_score = fields.Integer(
        string="Credit Score",
        compute='_compute_smart_credit_score',
        help="Payment behaviour score from 0 (poor) to 100 (excellent).")
    smart_suggested_limit = fields.Monetary(
        string="Suggested Limit",
        compute='_compute_smart_credit_score',
        currency_field='currency_id',
        help="Limit suggested by the smart scoring engine.")

    # ------------------------------------------------------------------
    # Credit hold
    # ------------------------------------------------------------------
    is_credit_hold = fields.Boolean(
        string="Credit Hold",
        tracking=True, copy=False,
        help="When on hold, sale confirmations and outgoing deliveries "
             "are stopped for this customer.")
    credit_hold_source = fields.Selection(
        selection=[('manual', 'Manual'), ('auto', 'Automatic (Aging Rule)')],
        string="Hold Source", copy=False)
    credit_hold_reason = fields.Char(string="Hold Reason", copy=False)
    credit_hold_date = fields.Datetime(string="Hold Since", copy=False)

    # ------------------------------------------------------------------
    # Relations
    # ------------------------------------------------------------------
    credit_extension_ids = fields.One2many(
        'inom.credit.extension', 'partner_id',
        string="Credit Extensions")
    credit_audit_count = fields.Integer(
        compute='_compute_credit_audit_count', string="Audit Entries")

    # ==================================================================
    # Helpers
    # ==================================================================
    def _smart_credit_family(self):
        """All partners of the same commercial entity (parent + contacts)."""
        self.ensure_one()
        commercial = self.commercial_partner_id
        return commercial | commercial.child_ids

    def _inom_credit_scope(self):
        """Every partner belonging to the commercial entities of ``self``.

        Batch counterpart of :meth:`_smart_credit_family`: it lets the
        compute methods run a single query over all related partners
        instead of one query per record.
        """
        commercials = self.commercial_partner_id
        # sudo(): walking the contact tree must not depend on the current
        # user's partner rules; only aggregated figures leave these methods.
        return (commercials | commercials.child_ids).sudo()

    def _smart_credit_effective_partner(self):
        """Partner record that actually carries the credit configuration.

        Priority: the partner itself, then its commercial parent.
        Returns an empty recordset when smart credit is disabled.
        """
        self.ensure_one()
        if self.use_smart_credit:
            return self
        commercial = self.commercial_partner_id
        if commercial != self and commercial.use_smart_credit:
            return commercial
        return self.browse()

    @api.model
    def _inom_get_param(self, key, default=''):
        # sudo(): system parameters are not readable by regular users, but
        # every credit checkpoint needs the configured policy.
        return self.env['ir.config_parameter'].sudo().get_param(
            'inom_smart_credit_limit.%s' % key, default)

    def _inom_resolve_action(self, checkpoint_value):
        """Map a checkpoint policy + partner mode to the effective action."""
        self.ensure_one()
        if checkpoint_value == 'off':
            return 'ok'
        if self.credit_enforcement in ('warn', 'block'):
            return self.credit_enforcement
        return checkpoint_value

    @api.model
    def _inom_manager_users(self):
        group = self.env.ref(
            'inom_smart_credit_limit.group_smart_credit_manager',
            raise_if_not_found=False)
        if not group:
            return self.env['res.users']
        if 'user_ids' in group._fields:
            return group.user_ids
        return group.users

    # ==================================================================
    # Batch data gathering - one query each, never inside a loop
    # ==================================================================
    def _inom_receivable_by_entity(self, family):
        """Open posted receivables, keyed by commercial partner id."""
        result = defaultdict(float)
        if not family:
            return result
        # ``credit`` is restricted to the accounting groups; ``family`` is
        # already sudo so a salesperson still sees the credit position.
        family.mapped('credit')  # single batched compute for the whole set
        for partner in family:
            result[partner.commercial_partner_id.id] += partner.credit
        return result

    def _inom_uninvoiced_by_entity(self, family, company, today):
        """Uninvoiced value of confirmed orders, keyed by commercial id."""
        result = defaultdict(float)
        if not family:
            return result
        # sudo(): a salesperson limited to their own documents must still
        # see the customer's whole exposure across every salesperson.
        orders = self.env['sale.order'].sudo().search([
            ('partner_id', 'in', family.ids),
            ('state', '=', 'sale'),
            ('company_id', '=', company.id),
        ])
        for order in orders:
            # Full committed value of the confirmed order minus the part
            # already posted as an invoice (that part is counted in the
            # receivable balance). Delivery progress is deliberately
            # ignored: a confirmed order is already a credit commitment.
            invoiced = order.amount_invoiced \
                if 'amount_invoiced' in order._fields else 0.0
            amount = max(order.amount_total - invoiced, 0.0)
            if order.currency_id and \
                    order.currency_id != company.currency_id:
                amount = order.currency_id._convert(
                    amount, company.currency_id, company, today)
            result[order.partner_id.commercial_partner_id.id] += amount
        return result

    def _inom_extensions_by_entity(self, family, today):
        """Active temporary extensions, keyed by commercial partner id."""
        result = defaultdict(float)
        if not family:
            return result
        # sudo(): extensions are manager-owned data, but their amounts feed
        # the credit position shown to every credit user.
        extensions = self.env['inom.credit.extension'].sudo().search([
            ('partner_id', 'in', family.ids),
            ('state', '=', 'active'),
            ('date_start', '<=', today),
            ('date_end', '>=', today),
        ])
        for extension in extensions:
            result[extension.partner_id.commercial_partner_id.id] += \
                extension.amount
        return result

    @api.model
    def _inom_empty_stats(self):
        """Blank statistics bucket for one commercial entity."""
        return {
            'open_count': 0, 'total_open': 0.0,
            'overdue_amount': 0.0, 'overdue_count': 0,
            'recent_total': 0, 'recent_paid': 0,
        }

    def _inom_collect_open_invoices(self, stats, family, company, today):
        """Fold the open invoice figures into ``stats`` (one query)."""
        # sudo(): scoring reads customer invoices, a model sales users have
        # no access to; only the resulting score leaves this method.
        open_moves = self.env['account.move'].sudo().search([
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted'),
            ('payment_state', 'in', ('not_paid', 'partial')),
            ('partner_id', 'in', family.ids),
            ('company_id', '=', company.id),
        ])
        for move in open_moves:
            key = move.partner_id.commercial_partner_id.id
            data = stats.setdefault(key, self._inom_empty_stats())
            data['open_count'] += 1
            data['total_open'] += move.amount_residual_signed
            if move.invoice_date_due and move.invoice_date_due < today:
                data['overdue_amount'] += move.amount_residual_signed
                data['overdue_count'] += 1

    def _inom_collect_recent_invoices(self, stats, family, company, today):
        """Fold the last 12 months of invoices into ``stats`` (one query)."""
        # sudo(): same rationale as the open invoice scan above.
        recent_moves = self.env['account.move'].sudo().search([
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted'),
            ('partner_id', 'in', family.ids),
            ('company_id', '=', company.id),
            ('invoice_date', '>=', today - timedelta(days=365)),
        ])
        for move in recent_moves:
            key = move.partner_id.commercial_partner_id.id
            data = stats.setdefault(key, self._inom_empty_stats())
            data['recent_total'] += 1
            if move.payment_state in ('paid', 'in_payment'):
                data['recent_paid'] += 1

    def _inom_payment_history(self, family, company, today):
        """Invoice statistics per commercial entity, gathered in 2 queries."""
        stats = {}
        if not family:
            return stats
        self._inom_collect_open_invoices(stats, family, company, today)
        self._inom_collect_recent_invoices(stats, family, company, today)
        return stats

    def _inom_worst_overdue_days(self, today):
        """Age of the oldest open invoice, keyed by commercial partner id."""
        result = {}
        family = self._inom_credit_scope()
        if not family:
            return result
        # sudo(): the nightly aging scan runs for every credit-controlled
        # customer regardless of the scheduler user's accounting rights.
        moves = self.env['account.move'].sudo().search([
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted'),
            ('payment_state', 'in', ('not_paid', 'partial')),
            ('partner_id', 'in', family.ids),
            ('invoice_date_due', '!=', False),
            ('invoice_date_due', '<', today),
        ])
        for move in moves:
            key = move.partner_id.commercial_partner_id.id
            days = (today - move.invoice_date_due).days
            if days > result.get(key, 0):
                result[key] = days
        return result

    # ==================================================================
    # Computes
    # ==================================================================
    @api.depends('use_smart_credit', 'smart_credit_limit',
                 'credit_extension_ids.amount', 'credit_extension_ids.state')
    def _compute_smart_credit_amounts(self):
        company = self.env.company
        today = fields.Date.context_today(self)
        family = self._inom_credit_scope()
        receivables = self._inom_receivable_by_entity(family)
        uninvoiced = self._inom_uninvoiced_by_entity(family, company, today)
        extensions = self._inom_extensions_by_entity(family, today)
        for partner in self:
            key = partner.commercial_partner_id.id
            exposure = receivables.get(key, 0.0) + uninvoiced.get(key, 0.0)
            extra = extensions.get(key, 0.0)
            effective_limit = partner.smart_credit_limit + extra
            partner.smart_credit_exposure = exposure
            partner.smart_extra_credit = extra
            partner.smart_available_credit = effective_limit - exposure
            if effective_limit > 0:
                partner.smart_credit_utilization = min(
                    100.0, max(0.0, exposure / effective_limit * 100.0))
            else:
                partner.smart_credit_utilization = 0.0

    @api.depends('use_smart_credit', 'smart_credit_limit',
                 'smart_credit_exposure')
    def _compute_smart_credit_score(self):
        company = self.env.company
        today = fields.Date.context_today(self)
        family = self._inom_credit_scope()
        history = self._inom_payment_history(family, company, today)
        for partner in self:
            stats = history.get(partner.commercial_partner_id.id)
            has_history = bool(
                stats and (stats['recent_total'] or stats['open_count']))
            if not has_history:
                # New customer without any history: neutral baseline.
                partner.smart_credit_score = 70
                partner.smart_suggested_limit = 0.0
                continue
            score = partner._inom_score_from_stats(stats)
            partner.smart_credit_score = score
            partner.smart_suggested_limit = \
                partner._inom_suggested_limit(score)

    def _inom_score_from_stats(self, stats):
        """Turn aggregated invoice statistics into a 0-100 score."""
        self.ensure_one()
        # Penalty 1 (max 40): share of the open amount that is overdue
        penalty_overdue_amt = 0.0
        if stats['total_open'] > 0:
            penalty_overdue_amt = 40.0 * min(
                1.0, stats['overdue_amount'] / stats['total_open'])
        # Penalty 2 (max 20): number of overdue invoices
        penalty_overdue_cnt = min(20.0, stats['overdue_count'] * 4.0)
        # Penalty 3 (max 20): high utilization of the limit
        penalty_util = 0.0
        limit = self.smart_credit_limit + self.smart_extra_credit
        if limit > 0:
            utilization = self.smart_credit_exposure / limit
            if utilization > 0.7:
                penalty_util = min(20.0, (utilization - 0.7) / 0.3 * 20.0)
        # Penalty 4 (max 20): paid ratio over the last 12 months
        penalty_paid = 0.0
        if stats['recent_total']:
            paid_ratio = stats['recent_paid'] / stats['recent_total']
            penalty_paid = 20.0 * (1.0 - paid_ratio)
        return int(round(max(0.0, 100.0 - penalty_overdue_amt
                             - penalty_overdue_cnt - penalty_util
                             - penalty_paid)))

    def _inom_suggested_limit(self, score):
        """Limit suggested for the given score, rounded to the hundred."""
        self.ensure_one()
        base_limit = self.smart_credit_limit
        if not self.use_smart_credit or base_limit <= 0:
            return 0.0
        if score >= 85:
            suggested = base_limit * 1.25
        elif score >= 70:
            suggested = base_limit
        elif score >= 50:
            suggested = base_limit * 0.9
        else:
            suggested = base_limit * 0.75
        return round(suggested / 100.0) * 100.0

    @api.depends('use_smart_credit')
    def _compute_credit_audit_count(self):
        counts = defaultdict(int)
        family = self._inom_credit_scope()
        if family:
            # sudo(): the audit log is manager-only data, but the counter
            # sits on the partner form of every credit user.
            groups = self.env['inom.credit.audit'].sudo()._read_group(
                [('partner_id', 'in', family.ids)],
                groupby=['partner_id'], aggregates=['__count'])
            for partner, count in groups:
                counts[partner.commercial_partner_id.id] += count
        for partner in self:
            partner.credit_audit_count = counts.get(
                partner.commercial_partner_id.id, 0)

    # ==================================================================
    # Central credit evaluation (used by SO / picking / invoice)
    # ==================================================================
    def _smart_credit_evaluate(self, extra_amount=0.0):
        """Evaluate the credit position of the effective partner.

        :param extra_amount: additional amount (company currency) that the
            calling document would add on top of the current exposure.
        :return: dict with keys ``enabled``, ``hold``, ``exceeded``,
            ``partner`` (effective partner), ``available``, ``over_amount``.
        """
        self.ensure_one()
        effective = self._smart_credit_effective_partner()
        if not effective:
            return {'enabled': False, 'hold': False, 'exceeded': False,
                    'partner': effective, 'available': 0.0,
                    'over_amount': 0.0}
        available = effective.smart_available_credit
        exceeded = extra_amount > available
        return {
            'enabled': True,
            'hold': effective.is_credit_hold,
            'exceeded': exceeded,
            'partner': effective,
            'available': available,
            'over_amount': max(0.0, extra_amount - available),
        }

    # ==================================================================
    # Buttons
    # ==================================================================
    def action_apply_suggested_limit(self):
        Audit = self.env['inom.credit.audit']
        by_limit = defaultdict(lambda: self.browse())
        for partner in self:
            if partner.smart_suggested_limit <= 0:
                continue
            Audit._log(
                partner, 'limit_update',
                amount=partner.smart_suggested_limit,
                note=_("Suggested limit applied (score %(score)s). "
                       "Previous limit: %(old)s",
                       score=partner.smart_credit_score,
                       old=partner.smart_credit_limit))
            by_limit[partner.smart_suggested_limit] |= partner
        # One write per distinct limit instead of one write per record.
        for new_limit, partners in by_limit.items():
            partners.smart_credit_limit = new_limit
        return True

    def action_credit_hold(self):
        Audit = self.env['inom.credit.audit']
        self.write({
            'is_credit_hold': True,
            'credit_hold_source': 'manual',
            'credit_hold_date': fields.Datetime.now(),
        })
        without_reason = self.filtered(lambda p: not p.credit_hold_reason)
        without_reason.credit_hold_reason = _("Manual credit hold")
        body = _("Customer placed on credit hold by %s.", self.env.user.name)
        for partner in self:
            Audit._log(partner, 'manual_hold',
                       note=partner.credit_hold_reason or '')
            partner.message_post(body=body)
        return True

    def action_credit_release(self):
        Audit = self.env['inom.credit.audit']
        self.write({
            'is_credit_hold': False,
            'credit_hold_source': False,
            'credit_hold_date': False,
            'credit_hold_reason': False,
        })
        body = _("Credit hold released by %s.", self.env.user.name)
        for partner in self:
            Audit._log(partner, 'manual_release')
            partner.message_post(body=body)
        return True

    def action_view_credit_audit(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id(
            'inom_smart_credit_limit.action_inom_credit_audit')
        action['domain'] = [
            ('partner_id', 'in', self._smart_credit_family().ids)]
        action['context'] = {'default_partner_id': self.id}
        return action

    # ==================================================================
    # Crons
    # ==================================================================
    @api.model
    def _inom_aging_settings(self):
        """Configured aging threshold and automatic release flag."""
        try:
            hold_days = int(self._inom_get_param('auto_hold_days', '60'))
        except (TypeError, ValueError):
            hold_days = 60
        auto_release = self._inom_get_param(
            'auto_release', 'True') in ('True', 'true', '1')
        return hold_days, auto_release

    def _inom_apply_auto_hold(self, reasons):
        """Place the given partners on automatic hold and notify managers."""
        if not self:
            return
        self.write({
            'is_credit_hold': True,
            'credit_hold_source': 'auto',
            'credit_hold_date': fields.Datetime.now(),
        })
        Audit = self.env['inom.credit.audit']
        managers = self._inom_manager_users()
        summary = _("Customer on automatic credit hold")
        for partner in self:
            reason = reasons[partner.id]
            partner.credit_hold_reason = reason
            Audit._log(partner, 'auto_hold', note=reason)
            partner.message_post(body=reason)
            for user in managers:
                partner.activity_schedule(
                    'mail.mail_activity_data_todo',
                    summary=summary, note=reason, user_id=user.id)

    def _inom_apply_auto_release(self):
        """Release partners whose aging is back below the threshold."""
        if not self:
            return
        self.write({
            'is_credit_hold': False,
            'credit_hold_source': False,
            'credit_hold_date': False,
            'credit_hold_reason': False,
        })
        Audit = self.env['inom.credit.audit']
        note = _("Automatic release: no invoice beyond the aging threshold.")
        body = _("Credit hold automatically released.")
        for partner in self:
            Audit._log(partner, 'auto_release', note=note)
            partner.message_post(body=body)

    @api.model
    def _inom_expire_extensions(self, today):
        """Close temporary extensions whose validity has run out."""
        # sudo(): the scheduler user is not necessarily a credit manager.
        expired = self.env['inom.credit.extension'].sudo().search([
            ('state', '=', 'active'),
            ('date_end', '<', today),
        ])
        if not expired:
            return
        expired.state = 'expired'
        Audit = self.env['inom.credit.audit']
        note = _("Temporary credit extension expired.")
        for extension in expired:
            Audit._log(extension.partner_id, 'extension',
                       amount=extension.amount, note=note)

    @api.model
    def _cron_smart_credit_daily(self):
        """Daily job: aging based auto hold / auto release and
        expiry of temporary credit extensions."""
        today = fields.Date.context_today(self)
        hold_days, auto_release = self._inom_aging_settings()
        partners = self.search([('use_smart_credit', '=', True)])
        overdue_days = partners._inom_worst_overdue_days(today)

        to_hold = self.browse()
        to_release = self.browse()
        reasons = {}
        for partner in partners:
            worst = overdue_days.get(partner.commercial_partner_id.id, 0)
            if hold_days > 0 and worst > hold_days \
                    and not partner.is_credit_hold:
                to_hold |= partner
                reasons[partner.id] = _(
                    "Automatic hold: invoice overdue for %(days)s days "
                    "(threshold %(threshold)s days).",
                    days=worst, threshold=hold_days)
            elif partner.is_credit_hold \
                    and partner.credit_hold_source == 'auto' \
                    and auto_release and worst <= hold_days:
                to_release |= partner

        to_hold._inom_apply_auto_hold(reasons)
        to_release._inom_apply_auto_release()
        self._inom_expire_extensions(today)
        return True

    @api.model
    def _cron_smart_credit_scoring(self):
        """Monthly job: notify credit managers when the suggested limit
        deviates significantly from the configured limit."""
        if self._inom_get_param('scoring_active', 'True') not in (
                'True', 'true', '1'):
            return True
        Audit = self.env['inom.credit.audit']
        managers = self._inom_manager_users()
        summary = _("Credit limit review suggested")
        partners = self.search([
            ('use_smart_credit', '=', True),
            ('smart_credit_limit', '>', 0),
        ])
        for partner in partners:
            suggested = partner.smart_suggested_limit
            limit = partner.smart_credit_limit
            if suggested <= 0 or not limit:
                continue
            if abs(suggested - limit) / limit < 0.2:
                continue
            note = _(
                "Smart scoring review: score %(score)s/100, current limit "
                "%(limit).2f, suggested limit %(suggested).2f.",
                score=partner.smart_credit_score,
                limit=limit, suggested=suggested)
            Audit._log(partner, 'suggestion', amount=suggested, note=note)
            for user in managers:
                partner.activity_schedule(
                    'mail.mail_activity_data_todo',
                    summary=summary, note=note, user_id=user.id)
        return True
