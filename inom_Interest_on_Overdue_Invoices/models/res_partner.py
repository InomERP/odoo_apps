from odoo import models, fields, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    interest_calculation = fields.Selection([
        ('use_default', 'Use Company Default'),
        ('enabled', 'Enabled'),
        ('disabled', 'Disabled'),
    ], string='Interest Calculation', default='use_default')

    partner_interest_rule_id = fields.Many2one(
        'overdue.interest.rule',
        string='Interest Rule',
        help='Override the default interest rule for this customer'
    )

    extra_grace_days = fields.Integer(string='Extra Grace Days', default=0)

    total_interest_charged = fields.Monetary(
        string='Total Interest Charged',
        compute='_compute_interest_totals',
        currency_field='currency_id'
    )

    pending_interest = fields.Monetary(
        string='Pending Interest',
        compute='_compute_interest_totals',
        currency_field='currency_id'
    )

    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.company.currency_id
    )

    interest_history_ids = fields.One2many(
        'inom.interest.history', 'partner_id', string='Interest History'
    )

    interest_count = fields.Integer(
        string='Interest Count',
        compute='_compute_interest_count'
    )

    @api.depends('interest_history_ids')
    def _compute_interest_count(self):
        for rec in self:
            rec.interest_count = len(rec.interest_history_ids)

    @api.depends('interest_history_ids.final_interest', 'interest_history_ids.status')
    def _compute_interest_totals(self):
        for rec in self:
            history = rec.interest_history_ids
            rec.total_interest_charged = sum(
                h.final_interest for h in history if h.status == 'applied'
            )
            rec.pending_interest = sum(
                h.final_interest for h in history if h.status == 'draft'
            )

    def action_view_interest_history(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Interest History',
            'res_model': 'inom.interest.history',
            'view_mode': 'list,form',
            'domain': [('partner_id', '=', self.id)],
            'context': {'default_partner_id': self.id},
        }

    def action_compute_interest(self):
        """Manually compute overdue interest for the selected customer(s)."""
        self.env['inom.interest.history'].compute_overdue_interest(partners=self)
        if len(self) == 1:
            return self.action_view_interest_history()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Interest History',
            'res_model': 'inom.interest.history',
            'view_mode': 'list,form',
            'domain': [('partner_id', 'in', self.ids)],
        }