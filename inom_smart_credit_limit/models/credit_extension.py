# -*- coding: utf-8 -*-
# Part of INOM Smart Credit Limit. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class InomCreditExtension(models.Model):
    _name = 'inom.credit.extension'
    _description = 'Temporary Credit Extension'
    _order = 'date_end desc, id desc'

    name = fields.Char(
        string="Reason", required=True,
        help="Business reason for granting the temporary extension, "
             "e.g. festive season order.")
    partner_id = fields.Many2one(
        'res.partner', string="Customer", required=True,
        ondelete='cascade', index=True)
    company_id = fields.Many2one(
        'res.company', string="Company", ondelete='cascade',
        default=lambda self: self.env.company, required=True)
    currency_id = fields.Many2one(
        related='company_id.currency_id', string="Currency",
        ondelete='set null')
    amount = fields.Monetary(
        string="Extra Amount", required=True,
        currency_field='currency_id')
    date_start = fields.Date(
        string="Valid From", required=True,
        default=fields.Date.context_today)
    date_end = fields.Date(string="Valid Until", required=True)
    state = fields.Selection(
        selection=[
            ('active', 'Active'),
            ('expired', 'Expired'),
            ('cancelled', 'Cancelled'),
        ],
        string="Status", default='active', required=True, copy=False)
    user_id = fields.Many2one(
        'res.users', string="Granted By", ondelete='set null',
        default=lambda self: self.env.user, readonly=True)

    @api.constrains('date_start', 'date_end')
    def _check_dates(self):
        for extension in self:
            if extension.date_end < extension.date_start:
                raise ValidationError(_(
                    "The end date of a credit extension cannot be "
                    "before its start date."))

    @api.constrains('amount')
    def _check_amount(self):
        for extension in self:
            if extension.amount <= 0:
                raise ValidationError(_(
                    "The extension amount must be positive."))

    @api.model_create_multi
    def create(self, vals_list):
        extensions = super().create(vals_list)
        Audit = self.env['inom.credit.audit']
        for extension in extensions:
            Audit._log(
                extension.partner_id, 'extension',
                amount=extension.amount,
                note=_("Temporary credit extension granted until %s: %s",
                       extension.date_end, extension.name))
        return extensions

    def action_cancel(self):
        Audit = self.env['inom.credit.audit']
        for extension in self:
            extension.state = 'cancelled'
            Audit._log(
                extension.partner_id, 'extension',
                amount=extension.amount,
                note=_("Temporary credit extension cancelled: %s",
                       extension.name))
        return True

    def action_reactivate(self):
        for extension in self:
            if extension.date_end >= fields.Date.context_today(self):
                extension.state = 'active'
        return True
