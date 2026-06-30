# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class InomContract(models.Model):
    _name = 'inom.contract'
    _description = 'Contract'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_start desc, id desc'

    name = fields.Char(
        string='Contract Reference',
        required=True,
        copy=False,
        readonly=True,
        index=True,
        default=lambda self: _('New'),
        tracking=True,
    )
    contract_type = fields.Selection(
        selection=[
            ('sale', 'Sale'),
            ('purchase', 'Purchase'),
            ('other', 'Other'),
        ],
        string='Type',
        default='sale',
        required=True,
        tracking=True,
    )
    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string='Partner',
        tracking=True,
        help='Customer or Vendor linked to this contract.',
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(
        comodel_name='res.currency',
        string='Currency',
        required=True,
        default=lambda self: self.env.company.currency_id,
    )
    user_id = fields.Many2one(
        comodel_name='res.users',
        string='Responsible',
        default=lambda self: self.env.user,
        tracking=True,
    )
    date_start = fields.Date(
        string='Start Date',
        default=fields.Date.context_today,
        tracking=True,
    )
    date_end = fields.Date(
        string='End Date',
        tracking=True,
    )
    last_payment_date = fields.Date(
        string='Last Payment Date',
        tracking=True,
    )
    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('confirm', 'Confirmed'),
            ('approval', 'Under Approval'),
            ('running', 'Running'),
            ('blocked', 'Blocked'),
            ('closed', 'Closed'),
            ('cancelled', 'Cancelled'),
        ],
        string='Status',
        default='draft',
        required=True,
        tracking=True,
        copy=False,
    )
    kanban_state = fields.Selection(
        selection=[
            ('normal', 'In Progress'),
            ('done', 'Ready'),
            ('blocked', 'Blocked'),
        ],
        string='Kanban State',
        default='normal',
        required=True,
        copy=False,
        help='Color indicator on the kanban card:\n'
             ' * In Progress: grey\n'
             ' * Ready: green\n'
             ' * Blocked: red',
    )
    description = fields.Html(
        string='Description',
    )
    use_lines = fields.Boolean(
        string='Use Lines',
        default=True,
        help='If enabled, contract lines can be added. '
             'If disabled, the Lines tab is hidden.',
    )
    payment_term_id = fields.Many2one(
        comodel_name='account.payment.term',
        string='Payment Terms',
    )
    template_id = fields.Many2one(
        comodel_name='inom.contract',
        string='Template',
        domain="[('is_template', '=', True)]",
        copy=False,
    )
    is_template = fields.Boolean(
        string='Is a Template',
        default=False,
    )
    visibility = fields.Selection(
        selection=[
            ('all', 'All Internal Users'),
            ('followers', 'Followers Only'),
        ],
        string='Visibility',
        default='all',
        required=True,
    )
    approval_team_id = fields.Many2one(
        comodel_name='inom.approval.team',
        string='Approval Team',
        tracking=True,
    )
    approver_ids = fields.One2many(
        comodel_name='inom.contract.approver',
        inverse_name='contract_id',
        string='Approvers',
        copy=False,
    )
    current_step = fields.Integer(
        string='Current Step',
        compute='_compute_current_step',
    )
    can_approve = fields.Boolean(
        string='Can Approve',
        compute='_compute_can_approve',
        search='_search_can_approve',
    )
    expiry_warning_sent = fields.Boolean(
        string='Expiry Warning Sent',
        default=False,
        copy=False,
    )
    invoice_ids = fields.One2many(
        comodel_name='account.move',
        inverse_name='contract_id',
        string='Invoices / Bills',
    )
    invoice_count = fields.Integer(
        string='Invoice Count',
        compute='_compute_invoice_count',
    )
    line_ids = fields.One2many(
        comodel_name='inom.contract.line',
        inverse_name='contract_id',
        string='Contract Lines',
        copy=True,
    )
    amount_untaxed = fields.Monetary(
        string='Untaxed Amount',
        compute='_compute_amounts',
        store=True,
        currency_field='currency_id',
    )
    amount_tax = fields.Monetary(
        string='Taxes',
        compute='_compute_amounts',
        store=True,
        currency_field='currency_id',
    )
    amount_total = fields.Monetary(
        string='Total',
        compute='_compute_amounts',
        store=True,
        currency_field='currency_id',
    )

    @api.depends('line_ids.price_subtotal', 'line_ids.price_tax')
    def _compute_amounts(self):
        for contract in self:
            untaxed = sum(contract.line_ids.mapped('price_subtotal'))
            taxes = sum(contract.line_ids.mapped('price_tax'))
            contract.amount_untaxed = untaxed
            contract.amount_tax = taxes
            contract.amount_total = untaxed + taxes

    def _compute_invoice_count(self):
        Move = self.env['account.move'].sudo()
        for contract in self:
            contract.invoice_count = Move.search_count(
                [('contract_id', '=', contract.id)]) if contract.id else 0

    @api.depends('approver_ids.status', 'approver_ids.step')
    def _compute_current_step(self):
        for contract in self:
            pending = contract.approver_ids.filtered(
                lambda a: a.status == 'pending')
            contract.current_step = min(pending.mapped('step')) if pending else 0

    @api.depends('approver_ids.status', 'approver_ids.step',
                 'approver_ids.user_id', 'state', 'current_step')
    def _compute_can_approve(self):
        for contract in self:
            can = False
            if contract.state == 'approval':
                can = bool(contract.approver_ids.filtered(
                    lambda a: a.step == contract.current_step
                    and a.user_id == self.env.user
                    and a.status == 'pending'))
            contract.can_approve = can

    def _search_can_approve(self, operator, value):
        if operator not in ('=', '!=') or not isinstance(value, bool):
            raise UserError(_('Unsupported search operation on "Can Approve".'))
        want_true = (operator == '=') == bool(value)
        candidates = self.search([
            ('state', '=', 'approval'),
            ('approver_ids.user_id', '=', self.env.user.id),
            ('approver_ids.status', '=', 'pending'),
        ])
        matching = candidates.filtered('can_approve')
        if want_true:
            return [('id', 'in', matching.ids)]
        return [('id', 'not in', matching.ids)]

    @api.onchange('template_id')
    def _onchange_template_id(self):
        for contract in self:
            template = contract.template_id
            if not template:
                continue
            if template.description and not contract.description:
                contract.description = template.description
            if not contract.contract_type:
                contract.contract_type = template.contract_type
            new_lines = [(5, 0, 0)]
            for line in template.line_ids:
                new_lines.append((0, 0, {
                    'product_id': line.product_id.id,
                    'name': line.name,
                    'quantity': line.quantity,
                    'price_unit': line.price_unit,
                    'tax_ids': [(6, 0, line.tax_ids.ids)],
                }))
            contract.line_ids = new_lines

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('is_template'):
                continue
            if not vals.get('name') or vals['name'] == _('New'):
                company_id = vals.get('company_id', self.env.company.id)
                seq = self.env['ir.sequence'].with_company(company_id)
                vals['name'] = seq.next_by_code('inom.contract') or _('New')
        return super().create(vals_list)

    # ------------------------------------------------------------------
    # Approval workflow helpers
    # ------------------------------------------------------------------
    def _approval_enabled(self):
        param = self.env['ir.config_parameter'].sudo().get_param(
            'inom_contract_management.use_contract_approval')
        return str(param).lower() in ('true', '1')

    def _should_use_approval(self):
        self.ensure_one()
        if not self.approval_team_id or not self.approval_team_id.approver_line_ids:
            return False
        return self._approval_enabled()

    def _generate_approvers(self):
        self.ensure_one()
        self.approver_ids.unlink()      
        vals = []
        for line in self.approval_team_id.approver_line_ids.sorted('sequence'):
            if not line.user_id:
                continue
            vals.append((0, 0, {
                'user_id': line.user_id.id,
                'role': line.role,
                'step': line.sequence,
                'step_name': line.role or line.user_id.name,
                'status': 'pending',
            }))
        self.approver_ids = vals

    def _notify_step_approvers(self, step):
        self.ensure_one()
        template = self.env.ref(
            'inom_contract_management.mail_template_contract_approval_request',
            raise_if_not_found=False)
        if not template:
            return
        approvers = self.approver_ids.filtered(
            lambda a: a.step == step and a.status == 'pending')
        partners = approvers.mapped('user_id.partner_id')
        if not partners:
            return
        template.send_mail(
            self.id, force_send=True,
            email_values={'partner_ids': [(6, 0, partners.ids)]})

    def _notify_approved(self):
        self.ensure_one()
        template = self.env.ref(
            'inom_contract_management.mail_template_contract_approved',
            raise_if_not_found=False)
        if template and self.user_id:
            template.send_mail(
                self.id, force_send=True,
                email_values={'partner_ids': [(6, 0, self.user_id.partner_id.ids)]})

    def _apply_return(self, comment):
        self.ensure_one()
        step = self.current_step
        line = self.approver_ids.filtered(
            lambda a: a.step == step and a.user_id == self.env.user
            and a.status == 'pending')
        if line:
            line.write({
                'status': 'returned',
                'date': fields.Datetime.now(),
                'comment': comment,
            })
        self.state = 'draft'
        self.message_post(
            body=_('Contract returned for correction: %s', comment or ''))
        template = self.env.ref(
            'inom_contract_management.mail_template_contract_returned',
            raise_if_not_found=False)
        if template and self.user_id:
            template.with_context(return_comment=comment).send_mail(
                self.id, force_send=True,
                email_values={'partner_ids': [(6, 0, self.user_id.partner_id.ids)]})

    # ------------------------------------------------------------------
    # Buttons
    # ------------------------------------------------------------------
    def action_confirm(self):
        for contract in self:
            if contract.state != 'draft':
                raise UserError(_('Only draft contracts can be confirmed.'))
            if contract._should_use_approval():
                contract._generate_approvers()
                contract.state = 'approval'
                contract._notify_step_approvers(contract.current_step)
            else:
                contract.state = 'confirm'

    def action_approve(self):
        for contract in self:
            if contract.state != 'approval':
                raise UserError(_('This contract is not awaiting approval.'))
            step = contract.current_step
            line = contract.approver_ids.filtered(
                lambda a: a.step == step and a.user_id == self.env.user
                and a.status == 'pending')
            if not line:
                raise UserError(
                    _('You are not an approver for the current step.'))
            line.write({'status': 'approved', 'date': fields.Datetime.now()})
            remaining_step = contract.approver_ids.filtered(
                lambda a: a.step == step and a.status == 'pending')
            if remaining_step:
                # other approvers of this step are still pending
                continue
            next_pending = contract.approver_ids.filtered(
                lambda a: a.status == 'pending')
            if next_pending:
                contract._notify_step_approvers(min(next_pending.mapped('step')))
            else:
                contract.state = 'running'
                contract._notify_approved()

    def action_return_correction(self):
        self.ensure_one()
        if self.state != 'approval':
            raise UserError(_('Only contracts under approval can be returned.'))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Return for Correction'),
            'res_model': 'inom.contract.return.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_contract_id': self.id},
        }

    def action_start(self):
        for contract in self:
            if contract.state not in ('confirm', 'approval', 'blocked'):
                raise UserError(_('This contract cannot be set to Running '
                                  'from its current state.'))
            contract.state = 'running'

    def action_block(self):
        for contract in self:
            if contract.state != 'running':
                raise UserError(_('Only running contracts can be blocked.'))
            contract.state = 'blocked'

    def action_close(self):
        self.write({'state': 'closed'})

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def action_draft(self):
        self.write({'state': 'draft'})

    def action_view_invoices(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Invoices / Bills'),
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('contract_id', '=', self.id)],
            'context': {'default_contract_id': self.id},
        }
    def action_renew(self):
        for contract in self:
            if contract.state not in ('blocked', 'closed'):
                raise UserError(_('Only blocked or closed contracts can be renewed.'))
            contract.write({'state': 'draft'})
            contract.message_post(
                body=_('Contract marked for renewal. Please resubmit for approval.'))

    def action_create_invoice(self):
        self.ensure_one()
        if self.state != 'running':
            raise UserError(_('Only running contracts can be invoiced.'))
        use_invoice = self.env['ir.config_parameter'].sudo().get_param(
            'inom_contract_management.use_contract_for_invoice')
        if not use_invoice:
            raise UserError(_(
                'Please enable "Use on Invoices" in Contracts Settings first.'))
        move_type = 'out_invoice' if self.contract_type == 'sale' else 'in_invoice'
        invoice = self.env['account.move'].create({
            'move_type': move_type,
            'currency_id': self.currency_id.id,
            'company_id': self.company_id.id,
            'contract_id': self.id,
        })
        return {
            'type': 'ir.actions.act_window',
            'name': _('Invoice'),
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': invoice.id,
        }

    def action_check_expiry(self):
        today = fields.Date.context_today(self)
        running = self.search([
            ('state', '=', 'running'), ('is_template', '=', False)])
        for contract in running:
            if not contract.date_end:
                continue
            days_left = (contract.date_end - today).days
            if days_left <= 7:
                contract.write({'state': 'blocked'})
                contract.activity_schedule(
                    'mail.mail_activity_data_todo',
                    date_deadline=contract.date_end,
                    summary=_('Contract Expiring Soon'),
                    note=_('Contract %s is expiring on %s.') % (
                        contract.name, contract.date_end),
                    user_id=contract.user_id.id or self.env.uid,
                )
                contract.message_post(
                    body=_('Contract blocked: expiring within 7 days (%s).') % (
                        contract.date_end))
        blocked = self.search([
            ('state', '=', 'blocked'), ('is_template', '=', False)])
        for contract in blocked:
            if contract.date_end and contract.date_end < today:
                contract.write({'state': 'closed'})
                contract.message_post(
                    body=_('Contract automatically closed: end date passed.'))
        running2 = self.search([
            ('state', '=', 'running'), ('is_template', '=', False)])
        for contract in running2:
            if contract.last_payment_date and contract.last_payment_date < today:
                contract.write({'state': 'closed'})
                contract.message_post(
                    body=_('Contract closed: last payment date passed.'))

    # ------------------------------------------------------------------
    # Scheduled action
    # ------------------------------------------------------------------
    @api.model
    def _cron_contract_expiry_warning(self):
        today = fields.Date.context_today(self)
        limit = today + timedelta(days=7)
        template = self.env.ref(
            'inom_contract_management.mail_template_contract_expiry',
            raise_if_not_found=False)
        if not template:
            return
        contracts = self.search([
            ('state', '=', 'running'),
            ('date_end', '!=', False),
            ('date_end', '>=', today),
            ('date_end', '<=', limit),
            ('expiry_warning_sent', '=', False),
        ])
        for contract in contracts:
            if contract.user_id:
                template.send_mail(
                    contract.id, force_send=True,
                    email_values={
                        'partner_ids': [(6, 0, contract.user_id.partner_id.ids)]})
            contract.expiry_warning_sent = True