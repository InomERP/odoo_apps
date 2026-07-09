# -*- coding: utf-8 -*-
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class InomAssetDepreciationLine(models.Model):
    _name = 'inom.asset.depreciation.line'
    _description = 'Asset Depreciation Line'
    _order = 'depreciation_date, id'

    asset_id = fields.Many2one(
        'inom.asset', string='Asset', required=True, ondelete='cascade')
    depreciation_date = fields.Date(string='Depreciation Date', required=True)
    amount = fields.Monetary(
        string='Depreciation Amount', currency_field='currency_id')
    accumulated_amount = fields.Monetary(
        string='Accumulated', currency_field='currency_id')
    remaining_value = fields.Monetary(
        string='Book Value After', currency_field='currency_id')
    state = fields.Selection([
        ('draft', 'Scheduled'),
        ('posted', 'Posted'),
    ], string='Status', default='draft')
    posted_on = fields.Datetime(string='Posted On', readonly=True)
    currency_id = fields.Many2one(
        related='asset_id.currency_id', store=True)
    company_id = fields.Many2one(
        related='asset_id.company_id', store=True)

    @api.model
    def generate_schedule(self, asset):
        """(Re)build the depreciation schedule of an asset. Already posted
        lines are preserved; only draft lines are regenerated."""
        posted = asset.depreciation_line_ids.filtered(
            lambda l: l.state == 'posted')
        asset.depreciation_line_ids.filtered(
            lambda l: l.state == 'draft').unlink()

        depreciable_base = (asset.purchase_value or 0.0) - \
            (asset.salvage_value or 0.0)
        already_taken = sum(posted.mapped('amount'))
        remaining = depreciable_base - already_taken
        if remaining <= 0:
            raise UserError(_(
                'Nothing left to depreciate on asset %s.',
                asset.display_name))

        months_total = (asset.depreciation_years or 5) * 12
        months_done = len(posted)
        months_left = months_total - months_done
        if months_left <= 0:
            raise UserError(_(
                'The configured asset life is already fully covered by '
                'posted lines.'))

        if posted:
            last_date = max(posted.mapped('depreciation_date'))
            start = last_date + relativedelta(months=1)
            book_value = (asset.purchase_value or 0.0) - already_taken
        else:
            start = asset.depreciation_start_date
            book_value = asset.purchase_value or 0.0

        accumulated = already_taken
        lines = []
        if asset.depreciation_method == 'linear':
            monthly = remaining / months_left
            for i in range(months_left):
                amount = monthly
                if i == months_left - 1:  # absorb rounding on last line
                    amount = remaining - monthly * (months_left - 1)
                accumulated += amount
                book_value -= amount
                lines.append({
                    'asset_id': asset.id,
                    'depreciation_date': start + relativedelta(months=i),
                    'amount': amount,
                    'accumulated_amount': accumulated,
                    'remaining_value': book_value,
                })
        else:  # declining balance with straight line floor on last period
            annual_rate = (asset.declining_factor or 2.0) / \
                (asset.depreciation_years or 5)
            monthly_rate = annual_rate / 12.0
            floor = asset.salvage_value or 0.0
            for i in range(months_left):
                amount = book_value * monthly_rate
                if book_value - amount < floor or i == months_left - 1:
                    amount = max(book_value - floor, 0.0)
                if amount <= 0:
                    break
                accumulated += amount
                book_value -= amount
                lines.append({
                    'asset_id': asset.id,
                    'depreciation_date': start + relativedelta(months=i),
                    'amount': amount,
                    'accumulated_amount': accumulated,
                    'remaining_value': book_value,
                })
        self.create(lines)
        asset.message_post(body=_(
            'Depreciation schedule generated: %s draft lines.', len(lines)))

    def action_post(self):
        self.write({
            'state': 'posted',
            'posted_on': fields.Datetime.now(),
        })

    def action_reset_draft(self):
        self.write({'state': 'draft', 'posted_on': False})

    @api.model
    def _cron_post_due_lines(self):
        today = fields.Date.context_today(self)
        due_lines = self.search([
            ('state', '=', 'draft'),
            ('depreciation_date', '<=', today),
        ])
        due_lines.action_post()
