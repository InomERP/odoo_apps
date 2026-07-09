# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class InomWorkPermit(models.Model):
    _name = 'inom.work.permit'
    _description = 'Safety Work Permit'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char(
        string='Permit Reference', required=True, copy=False,
        readonly=True, default=lambda self: _('New'))
    work_order_id = fields.Many2one(
        'inom.work.order', string='Work Order', required=True,
        ondelete='cascade')
    asset_id = fields.Many2one(
        related='work_order_id.asset_id', store=True)
    permit_type = fields.Selection([
        ('general', 'General Work'),
        ('hot_work', 'Hot Work'),
        ('electrical', 'Electrical Work'),
        ('height', 'Work at Height'),
        ('confined', 'Confined Space'),
        ('loto', 'Lockout / Tagout (LOTO)'),
    ], string='Permit Type', default='general', required=True,
        tracking=True)
    hazard_description = fields.Text(string='Identified Hazards')
    safety_measures = fields.Text(string='Safety Precautions')
    isolation_points = fields.Text(
        string='Isolation Points',
        help='For LOTO permits list every energy isolation point that must '
             'be locked and tagged.')
    valid_from = fields.Datetime(string='Valid From')
    valid_until = fields.Datetime(string='Valid Until')
    issued_by_id = fields.Many2one(
        'res.users', string='Issued By',
        default=lambda self: self.env.user, readonly=True)
    authorized_by_id = fields.Many2one(
        'res.users', string='Authorized By', readonly=True, copy=False)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('requested', 'Requested'),
        ('approved', 'Approved'),
        ('active', 'Active'),
        ('closed', 'Closed'),
        ('rejected', 'Rejected'),
    ], string='Status', default='draft', tracking=True)
    company_id = fields.Many2one(
        'res.company', string='Company', required=True,
        default=lambda self: self.env.company)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'inom.work.permit') or _('New')
        return super().create(vals_list)

    def action_request(self):
        self.write({'state': 'requested'})

    def action_approve(self):
        if not self.env.user.has_group(
                'inom_asset_care.group_asset_manager'):
            raise UserError(_('Only Asset Managers can approve permits.'))
        self.write({
            'state': 'approved',
            'authorized_by_id': self.env.user.id,
        })

    def action_activate(self):
        for permit in self.filtered(lambda p: p.state == 'approved'):
            permit.state = 'active'

    def action_close(self):
        self.write({'state': 'closed'})

    def action_reject(self):
        self.write({'state': 'rejected'})

    @api.model
    def _cron_expire_permits(self):
        now = fields.Datetime.now()
        expired = self.search([
            ('state', 'in', ('approved', 'active')),
            ('valid_until', '!=', False),
            ('valid_until', '<', now),
        ])
        for permit in expired:
            permit.state = 'closed'
            permit.message_post(body=_(
                'Permit automatically closed because its validity period '
                'has ended.'))
