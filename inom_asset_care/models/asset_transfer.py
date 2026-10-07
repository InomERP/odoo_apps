# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class InomAssetTransfer(models.Model):
    _name = 'inom.asset.transfer'
    _description = 'Asset Transfer'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'transfer_date desc, id desc'

    name = fields.Char(
        string='Transfer Reference', required=True, copy=False,
        readonly=True, default=lambda self: _('New'))
    asset_id = fields.Many2one(
        'inom.asset', string='Asset', required=True, tracking=True,
        domain="[('state', '!=', 'scrapped')]")
    transfer_type = fields.Selection([
        ('location', 'Location Change'),
        ('custody', 'Custody Change'),
        ('both', 'Location + Custody'),
    ], string='Transfer Type', default='both', required=True)
    source_location_id = fields.Many2one(
        'inom.asset.location', string='From Location',
        compute='_compute_source', store=True, readonly=False)
    destination_location_id = fields.Many2one(
        'inom.asset.location', string='To Location', tracking=True)
    source_employee_id = fields.Many2one(
        'hr.employee', string='From Custodian',
        compute='_compute_source', store=True, readonly=False)
    destination_employee_id = fields.Many2one(
        'hr.employee', string='To Custodian', tracking=True)
    transfer_date = fields.Datetime(
        string='Transfer Date', default=fields.Datetime.now, required=True)
    reason = fields.Text(string='Reason for Transfer')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('waiting', 'Waiting Approval'),
        ('approved', 'Approved'),
        ('done', 'Completed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True)
    approved_by_id = fields.Many2one(
        'res.users', string='Approved By', readonly=True, copy=False)
    approved_on = fields.Datetime(string='Approved On', readonly=True, copy=False)
    company_id = fields.Many2one(
        'res.company', string='Company', required=True,
        default=lambda self: self.env.company)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'inom.asset.transfer') or _('New')
        return super().create(vals_list)

    @api.depends('asset_id')
    def _compute_source(self):
        for transfer in self:
            transfer.source_location_id = transfer.asset_id.location_id
            transfer.source_employee_id = transfer.asset_id.assigned_employee_id

    def action_submit(self):
        for transfer in self:
            transfer._check_destination()
        self.write({'state': 'waiting'})

    def action_approve(self):
        if not self.env.user.has_group(
                'inom_asset_care.group_asset_manager'):
            raise UserError(_(
                'Only Asset Managers can approve transfers.'))
        self.write({
            'state': 'approved',
            'approved_by_id': self.env.user.id,
            'approved_on': fields.Datetime.now(),
        })

    def action_complete(self):
        for transfer in self:
            if transfer.state != 'approved':
                raise UserError(_(
                    'Transfer %s must be approved before completion.',
                    transfer.name))
            vals = {}
            if transfer.transfer_type in ('location', 'both') \
                    and transfer.destination_location_id:
                vals['location_id'] = transfer.destination_location_id.id
            if transfer.transfer_type in ('custody', 'both') \
                    and transfer.destination_employee_id:
                vals['assigned_employee_id'] = \
                    transfer.destination_employee_id.id
            transfer.asset_id.write(vals)
            transfer.asset_id.message_post(body=_(
                'Asset moved via transfer %s: location %s, custodian %s.',
                transfer.name,
                transfer.destination_location_id.complete_name or '-',
                transfer.destination_employee_id.name or '-'))
        self.write({'state': 'done'})

    def action_cancel(self):
        self.filtered(
            lambda t: t.state not in ('done',)).write({'state': 'cancelled'})

    def action_reset_draft(self):
        self.filtered(
            lambda t: t.state == 'cancelled').write({'state': 'draft'})

    def action_notify_whatsapp(self):
        self.ensure_one()
        message = _(
            'Asset Transfer %(ref)s\nAsset: %(asset)s\n'
            'New Location: %(location)s\nNew Custodian: %(employee)s\n'
            'Date: %(date)s',
            ref=self.name, asset=self.asset_id.display_name,
            location=self.destination_location_id.complete_name or '-',
            employee=self.destination_employee_id.name or '-',
            date=fields.Datetime.to_string(self.transfer_date))
        phone = self.destination_employee_id.mobile_phone \
            or self.destination_employee_id.work_phone
        return self.asset_id._open_whatsapp_link(phone, message)

    def _check_destination(self):
        self.ensure_one()
        if self.transfer_type in ('location', 'both') \
                and not self.destination_location_id:
            raise UserError(_('Destination location is required.'))
        if self.transfer_type in ('custody', 'both') \
                and not self.destination_employee_id:
            raise UserError(_('Destination custodian is required.'))
