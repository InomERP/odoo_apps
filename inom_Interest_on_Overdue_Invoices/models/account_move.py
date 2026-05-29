# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class AccountMove(models.Model):
    _inherit = 'account.move'

    inom_interest_exclude = fields.Boolean(
        string="Exclude from Interest", copy=False,
        help="If set, this invoice is never charged overdue interest.")

    inom_interest_rule_id = fields.Many2one(
        'overdue.interest.rule', string="Interest Rule", copy=False,
        help="Override the interest rule for THIS invoice only.")

    inom_interest_history_ids = fields.One2many(
        'inom.interest.history', 'invoice_id', string="Interest History")

    inom_interest_count = fields.Integer(
        string="Interest Count", compute='_compute_inom_interest_count')

    inom_days_overdue = fields.Integer(
        string="Days Overdue", compute='_compute_inom_overdue')

    inom_interest_status = fields.Selection([
        ('no_interest', 'No Interest'),
        ('overdue', 'Overdue'),
        ('applied', 'Applied'),
    ], string="Interest Status", compute='_compute_inom_overdue')

    @api.depends('inom_interest_history_ids')
    def _compute_inom_interest_count(self):
        for move in self:
            move.inom_interest_count = len(move.inom_interest_history_ids)

    @api.depends('invoice_date_due', 'state', 'move_type', 'payment_state',
                 'amount_residual', 'inom_interest_exclude',
                 'inom_interest_history_ids.status')
    def _compute_inom_overdue(self):
        today = fields.Date.context_today(self)
        for move in self:
            days = 0
            if move.move_type == 'out_invoice' and move.invoice_date_due:
                days = max((today - move.invoice_date_due).days, 0)

            if move.inom_interest_history_ids.filtered(lambda h: h.status == 'applied'):
                status = 'applied'
            elif (move.move_type == 'out_invoice'
                  and move.state == 'posted'
                  and move.payment_state in ('not_paid', 'partial')
                  and move.amount_residual > 0
                  and days > 0
                  and not move.inom_interest_exclude):
                status = 'overdue'
            else:
                status = 'no_interest'

            move.inom_days_overdue = days
            move.inom_interest_status = status

    # ─────────────────────────────────────────────────────────────────────────
    #  Helper
    # ─────────────────────────────────────────────────────────────────────────

    def _inom_notify(self, title, message, kind='info'):
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {'title': title, 'message': message, 'type': kind, 'sticky': False},
        }

    def _inom_check_eligibility(self):
        """
        Har eligibility condition check karo aur
        clear error message return karo.
        Returns (True, None) if OK, else (False, notify_action).
        """
        self.ensure_one()


        if self.move_type != 'out_invoice' or self.state != 'posted':
            return False, self._inom_notify(
                _("Not Applicable"),
                _("Interest sirf confirmed (posted) customer invoices par apply hota hai."),
                kind='warning')

        # 2. Invoice already paid?
        if self.payment_state not in ('not_paid', 'partial') or self.amount_residual <= 0:
            return False, self._inom_notify(
                _("Already Paid"),
                _("Yeh invoice already fully paid hai. Interest applicable nahi hai."),
                kind='warning')

        # 3. Due date set hai?
        if not self.invoice_date_due:
            return False, self._inom_notify(
                _("No Due Date"),
                _("Interest apply karne se pehle invoice par Due Date set karo."),
                kind='warning')

        # 4. Invoice overdue hai?
        today = fields.Date.context_today(self)
        if self.invoice_date_due >= today:
            return False, self._inom_notify(
                _("Not Overdue"),
                _("Yeh invoice abhi overdue nahi hai. Due date abhi nahi gayi."),
                kind='warning')

        # 5. Exclude flag
        if self.inom_interest_exclude:
            return False, self._inom_notify(
                _("Excluded"),
                _("Is invoice par 'Exclude from Interest' flag set hai."),
                kind='warning')


        settings = self.env['inom.interest.history']._get_settings()
        if not settings['enabled']:
            return False, self._inom_notify(
                _("Feature Disabled"),
                _("Pehle 'Interest on Overdue Invoices' enable karo: "
                  "Invoicing > Configuration > Settings > Overdue Interest."),
                kind='warning')


        rule = (self.inom_interest_rule_id
                or self.env['inom.interest.history']._resolve_rule(
                    self.partner_id, settings['default_rule']))
        if not rule:
            return False, self._inom_notify(
                _("No Interest Rule"),
                _("Koi interest rule nahi mila. "
                  "Settings mein Default Interest Rule set karo, "
                  "ya is invoice / customer par rule assign karo."),
                kind='warning')

        return True, None

    # ─────────────────────────────────────────────────────────────────────────
    #  Button actions
    # ─────────────────────────────────────────────────────────────────────────

    def action_inom_preview_interest(self):
        """Preview Interest button — opens wizard in preview mode."""
        self.ensure_one()
        ok, err = self._inom_check_eligibility()
        if not ok:
            return err

        vals = self.env['inom.interest.history']._evaluate_invoice(self)
        if not vals:
            return self._inom_notify(
                _("No Interest"),
                _("Is invoice par abhi koi overdue interest applicable nahi hai."),
                kind='warning')

        return {
            'type': 'ir.actions.act_window',
            'name': _("Interest Preview"),
            'res_model': 'inom.apply.interest.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_invoice_id': self.id,
                'default_mode': 'preview',
            },
        }

    def action_inom_apply_interest(self):
        """Apply Interest button — opens wizard in apply mode."""
        self.ensure_one()
        ok, err = self._inom_check_eligibility()
        if not ok:
            return err

        vals = self.env['inom.interest.history']._evaluate_invoice(self)
        if not vals:
            return self._inom_notify(
                _("No Interest"),
                _("Is invoice par abhi koi overdue interest applicable nahi hai."),
                kind='warning')

        return {
            'type': 'ir.actions.act_window',
            'name': _("Apply Overdue Interest"),
            'res_model': 'inom.apply.interest.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_invoice_id': self.id,
                'default_mode': 'apply',
            },
        }

    def action_view_inom_interest(self):
        """Smart button — opens interest history for this invoice."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _("Interest Calculations"),
            'res_model': 'inom.interest.history',
            'view_mode': 'tree,form',
            'domain': [('invoice_id', '=', self.id)],
            'context': {'default_invoice_id': self.id},
        }