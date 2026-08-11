# -*- coding: utf-8 -*-
# Part of INOM Smart Credit Limit. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class InomCreditAudit(models.Model):
    _name = 'inom.credit.audit'
    _description = 'Credit Audit Log'
    _order = 'create_date desc, id desc'

    partner_id = fields.Many2one(
        'res.partner', string="Customer", required=True,
        ondelete='cascade', index=True)
    company_id = fields.Many2one(
        'res.company', string="Company", ondelete='cascade',
        default=lambda self: self.env.company, required=True)
    currency_id = fields.Many2one(
        related='company_id.currency_id', string="Currency",
        ondelete='set null')
    event = fields.Selection(
        selection=[
            ('warn', 'Warning Raised'),
            ('block', 'Confirmation Blocked'),
            ('approval_request', 'Approval Requested'),
            ('override', 'Manager Override'),
            ('manual_hold', 'Manual Hold'),
            ('manual_release', 'Manual Release'),
            ('auto_hold', 'Automatic Hold'),
            ('auto_release', 'Automatic Release'),
            ('limit_update', 'Limit Updated'),
            ('extension', 'Credit Extension'),
            ('suggestion', 'Scoring Suggestion'),
        ],
        string="Event", required=True, index=True)
    amount = fields.Monetary(
        string="Amount", currency_field='currency_id')
    document_ref = fields.Char(string="Document")
    note = fields.Text(string="Details")
    user_id = fields.Many2one(
        'res.users', string="User", ondelete='set null',
        default=lambda self: self.env.user, readonly=True)

    @api.model
    def _log(self, partner, event, amount=0.0, note='', document=None):
        """Create an audit entry with elevated rights so that every
        credit event is recorded regardless of the current user's ACL."""
        if not partner:
            return self.browse()
        return self.sudo().create({
            'partner_id': partner.commercial_partner_id.id or partner.id,
            'event': event,
            'amount': amount,
            'note': note,
            'document_ref': document.display_name if document else False,
            'user_id': self.env.user.id,
            'company_id': self.env.company.id,
        })
