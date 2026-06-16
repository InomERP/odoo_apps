# -*- coding: utf-8 -*-

from odoo import models, fields


class ResUsersSignature(models.Model):
    _name        = 'res.users.signature'
    _description = 'Per-Company Email Signature'
    _rec_name    = 'company_id'

    user_id = fields.Many2one(
        comodel_name='res.users',
        string='User',
        required=True,
        ondelete='cascade',
        index=True,
    )

    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company',
        required=True,
        ondelete='cascade',
        index=True,
        default=lambda self: self.env.company,
    )

    signature = fields.Text(
        string='Email Signature',
    )

    _sql_constraints = [
        (
            'user_company_uniq',
            'UNIQUE(user_id, company_id)',
            'Only one signature per user per company is allowed.',
        )
    ]