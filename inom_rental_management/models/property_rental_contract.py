from dateutil.relativedelta import relativedelta

from odoo import Command, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError

from .property_rent_schedule import PERIOD_MONTHS, months_between

# Contracts that hold the property for their dates: they may not overlap.
ACTIVE_STATES = ('approved', 'running', 'expired')
LOCKED_AFTER_DRAFT = (
    'property_id', 'tenant_id', 'date_start', 'date_end', 'rent_amount', 'rent_period',
    'deposit_amount', 'company_id', 'invoice_from',
)
BILLING_GROUP = 'account.group_account_invoice'
MANAGER_GROUP = 'inom_rental_management.group_rental_manager'


class PropertyRentalContract(models.Model):
    _name = 'property.rental.contract'
    _description = 'Rental Contract'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_start desc, id desc'
    _check_company_auto = True

    name = fields.Char(string='Reference', required=True, readonly=True, copy=False, default='/')
    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('approved', 'Approved'),
            ('running', 'Running'),
            ('expired', 'Expired'),
            ('terminated', 'Terminated'),
            ('closed', 'Closed'),
            ('cancelled', 'Cancelled'),
        ],
        required=True, default='draft', copy=False, tracking=True, index=True,
    )
    company_id = fields.Many2one(
        'res.company', required=True, index=True,
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(related='company_id.currency_id')
    user_id = fields.Many2one(
        'res.users', string='Responsible', tracking=True, index=True,
        default=lambda self: self.env.user,
        domain="[('share', '=', False)]",
    )
    property_id = fields.Many2one(
        'property.property', required=True, tracking=True, index=True, check_company=True,
        domain="[('property_for', '=', 'rent')]",
    )
    owner_id = fields.Many2one(related='property_id.owner_id', store=True, string='Owner')
    tenant_id = fields.Many2one(
        'res.partner', string='Tenant', required=True, tracking=True, check_company=True,
        index=True, ondelete='restrict',
        domain="[('is_tenant', '=', True)]",
    )
    date_start = fields.Date(string='Start Date', required=True, tracking=True, default=fields.Date.context_today)
    date_end = fields.Date(string='End Date', required=True, tracking=True)
    rent_period = fields.Selection(
        selection=[
            ('monthly', 'Monthly'),
            ('quarterly', 'Quarterly'),
            ('half_yearly', 'Half-Yearly'),
            ('yearly', 'Yearly'),
        ],
        string='Payment Frequency', required=True, default='monthly', tracking=True,
    )
    rent_amount = fields.Monetary(
        string='Monthly Rent', tracking=True,
        compute='_compute_rent_amount', store=True, readonly=False, precompute=True,
    )
    deposit_amount = fields.Monetary(string='Security Deposit', tracking=True)
    note = fields.Html(string='Terms and Conditions')
    lead_id = fields.Many2one(
        'crm.lead', string='Enquiry', index='btree_not_null', ondelete='set null', copy=False,
        check_company=True,
    )

    # Approval
    approved_by_id = fields.Many2one('res.users', string='Approved By', readonly=True, copy=False)
    date_approved = fields.Datetime(string='Approved On', readonly=True, copy=False)

    # Expiry
    days_to_expiry = fields.Integer(compute='_compute_days_to_expiry')

    # Renewal
    renewed_from_id = fields.Many2one(
        'property.rental.contract', string='Renewal Of', readonly=True, copy=False,
        index='btree_not_null', ondelete='restrict', check_company=True,
    )
    renewal_ids = fields.One2many('property.rental.contract', 'renewed_from_id', string='Renewals')
    renewal_id = fields.Many2one(
        'property.rental.contract', string='Renewed By', compute='_compute_renewal_id',
    )

    # Termination
    date_terminated = fields.Date(string='Termination Date', readonly=True, copy=False, tracking=True)
    termination_reason = fields.Selection(
        selection=[
            ('tenant_request', 'Tenant Request'),
            ('mutual', 'Mutual Agreement'),
            ('non_payment', 'Non-Payment'),
            ('breach', 'Breach of Contract'),
            ('property_sale', 'Property Sale'),
            ('other', 'Other'),
        ],
        readonly=True, copy=False, tracking=True,
    )
    termination_note = fields.Text(readonly=True, copy=False)
    date_closed = fields.Date(string='Closed On', readonly=True, copy=False)

    document_count = fields.Integer(compute='_compute_document_count')

    # Billing
    invoice_from = fields.Date(
        string='Invoice From',
        help="First rental period to invoice: periods starting before this date are left out of the billing "
             "schedule, for example when a lease is taken over part-way. Leave empty to invoice from the start date.",
    )
    rent_schedule_ids = fields.One2many('property.rent.schedule', 'contract_id', string='Billing Schedule')
    rental_move_ids = fields.One2many(
        'account.move', 'property_rental_contract_id', string='Invoices', groups=BILLING_GROUP,
    )
    invoice_count = fields.Integer(compute='_compute_invoice_count', compute_sudo=True)
    rent_invoiced = fields.Monetary(
        compute='_compute_rent_amounts', store=True,
        help="Untaxed rent of posted invoices, less posted credit notes.",
    )
    rent_received = fields.Monetary(string='Rent Collected', compute='_compute_rent_amounts', store=True)
    rent_due = fields.Monetary(string='Rent Outstanding', compute='_compute_rent_amounts', store=True)
    rent_overdue = fields.Monetary(compute='_compute_rent_overdue', compute_sudo=True)

    # Deposit
    deposit_invoiced = fields.Monetary(compute='_compute_deposit', store=True)
    deposit_received = fields.Monetary(compute='_compute_deposit', store=True)
    deposit_released = fields.Monetary(
        compute='_compute_deposit', store=True,
        help="Deposit released by posted settlements: refunded or credited to the tenant, plus deductions.",
    )
    deposit_deducted = fields.Monetary(compute='_compute_deposit', store=True)
    deposit_refunded = fields.Monetary(
        compute='_compute_deposit', store=True,
        help="Released deposit owed back to the tenant: paid out, or used against open invoices.",
    )
    deposit_held = fields.Monetary(compute='_compute_deposit', store=True)
    deposit_state = fields.Selection(
        selection=[
            ('none', 'No Deposit'),
            ('to_invoice', 'To Invoice'),
            ('invoiced', 'Awaiting Payment'),
            ('held', 'Held'),
            ('settled', 'Settled'),
        ],
        string='Deposit Status', compute='_compute_deposit', store=True,
    )

    _rent_amount_positive = models.Constraint(
        'CHECK(rent_amount >= 0)',
        'The rent cannot be negative.',
    )
    _deposit_amount_positive = models.Constraint(
        'CHECK(deposit_amount >= 0)',
        'The security deposit cannot be negative.',
    )

    @api.depends('property_id')
    def _compute_rent_amount(self):
        for contract in self:
            contract.rent_amount = contract.property_id.rent_price

    @api.depends('date_end', 'state')
    def _compute_days_to_expiry(self):
        today = fields.Date.context_today(self)
        for contract in self:
            if contract.state in ('approved', 'running', 'expired') and contract.date_end:
                contract.days_to_expiry = (contract.date_end - today).days
            else:
                contract.days_to_expiry = 0

    @api.depends('renewal_ids.state')
    def _compute_renewal_id(self):
        for contract in self:
            contract.renewal_id = contract.renewal_ids.filtered(lambda c: c.state != 'cancelled')[:1]

    def _compute_invoice_count(self):
        for contract in self:
            contract.invoice_count = len(contract.rental_move_ids)

    @api.depends(
        'rental_move_ids.state', 'rental_move_ids.property_rental_move_kind', 'rental_move_ids.amount_untaxed_signed',
        'rental_move_ids.amount_total_signed', 'rental_move_ids.amount_residual_signed',
    )
    def _compute_rent_amounts(self):
        for contract in self:
            moves = contract.rental_move_ids.filtered(
                lambda m: m.state == 'posted' and m.property_rental_move_kind == 'rent'
            )
            due = sum(moves.mapped('amount_residual_signed'))
            contract.rent_invoiced = sum(moves.mapped('amount_untaxed_signed'))
            contract.rent_due = due
            contract.rent_received = sum(moves.mapped('amount_total_signed')) - due

    @api.depends(
        'rental_move_ids.state', 'rental_move_ids.payment_state', 'rental_move_ids.invoice_date_due',
        'rental_move_ids.amount_residual_signed',
    )
    def _compute_rent_overdue(self):
        today = fields.Date.context_today(self)
        for contract in self:
            late = contract.rental_move_ids.filtered(
                lambda m: m.state == 'posted' and m.property_rental_move_kind == 'rent' and m.move_type == 'out_invoice'
                and m.payment_state in ('not_paid', 'partial') and m.invoice_date_due and m.invoice_date_due < today
            )
            contract.rent_overdue = sum(late.mapped('amount_residual_signed'))

    @api.depends(
        'deposit_amount', 'rental_move_ids.state', 'rental_move_ids.property_rental_move_kind',
        'rental_move_ids.amount_untaxed_signed', 'rental_move_ids.amount_total_signed',
        'rental_move_ids.amount_residual_signed', 'rental_move_ids.invoice_line_ids.price_subtotal',
    )
    def _compute_deposit(self):
        for contract in self:
            posted = contract.rental_move_ids.filtered(lambda m: m.state == 'posted')
            invoices = posted.filtered(lambda m: m.property_rental_move_kind == 'deposit' and m.move_type == 'out_invoice')
            settlements = posted.filtered(lambda m: m.property_rental_move_kind == 'deposit_settlement')
            deposit_product = settlements and contract.company_id._get_rental_product('deposit')
            deposit_lines = settlements.invoice_line_ids.filtered(lambda l: l.product_id == deposit_product)
            deduction_lines = settlements.invoice_line_ids - deposit_lines
            invoiced = sum(invoices.mapped('amount_untaxed_signed'))
            received = sum(invoices.mapped('amount_total_signed')) - sum(invoices.mapped('amount_residual_signed'))
            released = sum(deposit_lines.mapped('price_subtotal'))
            deducted = -sum(deduction_lines.mapped('price_subtotal'))
            contract.deposit_invoiced = invoiced
            contract.deposit_received = received
            contract.deposit_released = released
            contract.deposit_deducted = deducted
            contract.deposit_refunded = released - deducted
            contract.deposit_held = received - released
            currency = contract.currency_id
            if currency.is_zero(contract.deposit_amount) and not invoices:
                contract.deposit_state = 'none'
            elif settlements:
                contract.deposit_state = 'settled'
            elif not invoices:
                contract.deposit_state = 'to_invoice'
            elif currency.compare_amounts(received, invoiced) < 0:
                contract.deposit_state = 'invoiced'
            else:
                contract.deposit_state = 'held'

    def _compute_document_count(self):
        counts = dict(self.env['ir.attachment']._read_group(
            [('res_model', '=', self._name), ('res_id', 'in', self.ids)],
            groupby=['res_id'], aggregates=['__count'],
        ))
        for contract in self:
            contract.document_count = counts.get(contract.id, 0)

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------
    @api.constrains('date_start', 'date_end')
    def _check_dates(self):
        for contract in self:
            if contract.date_end and contract.date_start and contract.date_end <= contract.date_start:
                raise ValidationError(self.env._("The end date must be after the start date."))

    @api.constrains('tenant_id', 'property_id')
    def _check_tenant(self):
        for contract in self:
            tenant = contract.tenant_id
            if not tenant.is_tenant:
                raise ValidationError(self.env._(
                    "%(partner)s is not marked as a Tenant.", partner=tenant.display_name,
                ))
            owner = contract.property_id.owner_id
            if owner and tenant.commercial_partner_id == owner.commercial_partner_id:
                raise ValidationError(self.env._(
                    "%(partner)s owns %(property)s and cannot also be its tenant.",
                    partner=tenant.display_name, property=contract.property_id.display_name,
                ))

    @api.constrains('renewed_from_id', 'date_start', 'property_id', 'tenant_id')
    def _check_renewal(self):
        for contract in self.filtered('renewed_from_id'):
            previous = contract.renewed_from_id
            if contract.property_id != previous.property_id or contract.tenant_id != previous.tenant_id:
                raise ValidationError(self.env._("A renewal must keep the property and tenant of the contract it renews."))
            if contract.date_start <= previous.date_end:
                raise ValidationError(self.env._(
                    "The renewal must start after %(contract)s ends (%(date)s).",
                    contract=previous.name, date=previous.date_end,
                ))
            if len(previous.renewal_ids.filtered(lambda c: c.state != 'cancelled')) > 1:
                raise ValidationError(self.env._("%(contract)s already has a renewal.", contract=previous.name))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', '/') == '/':
                company = self.env['res.company'].browse(vals.get('company_id')) or self.env.company
                vals['name'] = self.env['ir.sequence'].with_company(company).next_by_code('property.rental.contract') or '/'
        return super().create(vals_list)

    def write(self, vals):
        locked = set(LOCKED_AFTER_DRAFT) & set(vals)
        if locked and any(contract.state != 'draft' for contract in self):
            raise UserError(self.env._(
                "The property, tenant, dates, rent and deposit of a contract cannot be changed once it is approved. "
                "Renew or terminate the contract instead."
            ))
        return super().write(vals)

    @api.ondelete(at_uninstall=False)
    def _unlink_keep_history(self):
        if any(contract.state not in ('draft', 'cancelled') for contract in self):
            raise UserError(self.env._(
                "Only draft or cancelled rental contracts can be deleted: the others are the rental history."
            ))

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _state_label(self, state):
        return dict(self._fields['state']._description_selection(self.env))[state]

    def _check_state(self, allowed, action):
        self.check_access('write')
        for contract in self:
            if contract.state not in allowed:
                raise UserError(self.env._(
                    "%(contract)s is %(state)s: you cannot %(action)s it.",
                    contract=contract.name, state=self._state_label(contract.state), action=action,
                ))

    def _check_manager(self, action):
        if not self.env.user.has_group(MANAGER_GROUP):
            raise AccessError(self.env._("Only Property Managers can %(action)s a rental contract.", action=action))

    def _lock_property(self):
        """ Write the property rows so that concurrent approvals or starts on the same property
        are serialised: the second transaction waits, then fails with a serialization error
        and is retried, at which point it sees the first contract and is refused. """
        self.env.cr.execute(
            'UPDATE property_property SET write_date = write_date WHERE id IN %s',
            [tuple(self.property_id.ids)],
        )

    def _check_no_overlap(self):
        Contract = self.sudo()
        for contract in self:
            if contract.property_id.allow_multiple_leases:
                continue
            overlapping = Contract.search([
                ('id', '!=', contract.id),
                ('property_id', '=', contract.property_id.id),
                ('state', 'in', ACTIVE_STATES),
                ('date_start', '<=', contract.date_end),
                ('date_end', '>=', contract.date_start),
            ], limit=1)
            if overlapping:
                raise UserError(self.env._(
                    "%(property)s already has an active rental contract (%(contract)s) for these dates.",
                    property=contract.property_id.display_name, contract=overlapping.name,
                ))

    def _check_tenant_identity(self):
        for contract in self:
            if contract.company_id.rental_require_tenant_identity \
                    and not contract.tenant_id._has_valid_identity_document(contract.date_start):
                raise UserError(self.env._(
                    "%(partner)s needs a valid identity document before the contract can start.",
                    partner=contract.tenant_id.display_name,
                ))

    def _release_property(self):
        """ Make the property available again unless another lease is still running on it. """
        for prop in self.property_id:
            still_let = self.sudo().search_count([
                ('property_id', '=', prop.id), ('state', 'in', ('running', 'expired')),
            ], limit=1)
            if not still_let and prop.state == 'rented':
                prop.sudo().state = 'available'

    # ------------------------------------------------------------------
    # Transitions
    # ------------------------------------------------------------------
    def action_approve(self):
        self._check_state(('draft',), self.env._("approve"))
        self._check_manager(self.env._("approve"))
        self._lock_property()
        self.sudo()._check_no_overlap()
        self.write({'state': 'approved', 'approved_by_id': self.env.user.id, 'date_approved': fields.Datetime.now()})

    def action_start(self):
        self._check_state(('draft', 'approved'), self.env._("start"))
        for contract in self:
            if contract.state == 'draft' and contract.company_id.rental_require_lease_approval:
                raise UserError(self.env._(
                    "%(contract)s must be approved by a Property Manager before it starts.", contract=contract.name,
                ))
        self._lock_property()
        self.sudo()._check_no_overlap()
        self.sudo()._check_tenant_identity()
        self.state = 'running'
        self.property_id.sudo().state = 'rented'
        self.lead_id.filtered(lambda lead: lead.won_status == 'pending').sudo().action_set_won()
        self.sudo()._generate_rent_schedule()
        # A renewal taking over closes the contract it renews once that one has ended.
        today = fields.Date.context_today(self)
        self.renewed_from_id.filtered(
            lambda c: c.state == 'expired' or (c.state == 'running' and c.date_end < today)
        ).sudo()._close()

    def action_close(self):
        self._check_state(('running', 'expired'), self.env._("close"))
        today = fields.Date.context_today(self)
        if any(contract.date_end > today for contract in self):
            self._check_manager(self.env._("close before its end date"))
        self._close()

    def _close(self):
        today = fields.Date.context_today(self)
        self.write({'state': 'closed', 'date_closed': today})
        for contract in self.filtered(lambda c: c.date_end > today):
            contract.sudo()._trim_rent_schedule(today)
        self._release_property()

    def action_cancel(self):
        self._check_state(('draft', 'approved'), self.env._("cancel"))
        self.state = 'cancelled'

    def action_reset_to_draft(self):
        self._check_state(('approved', 'cancelled'), self.env._("reset to draft"))
        if any(contract.state == 'approved' for contract in self):
            self._check_manager(self.env._("reset an approved contract to draft"))
        self.write({'state': 'draft', 'approved_by_id': False, 'date_approved': False})

    def action_open_renew_wizard(self):
        self.ensure_one()
        self._check_state(('running', 'expired'), self.env._("renew"))
        if self.renewal_id:
            raise UserError(self.env._(
                "%(contract)s is already renewed by %(renewal)s.", contract=self.name, renewal=self.renewal_id.name,
            ))
        return {
            'type': 'ir.actions.act_window',
            'name': self.env._("Renew %(contract)s", contract=self.name),
            'res_model': 'property.rental.contract.renew',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_contract_id': self.id},
        }

    def action_open_terminate_wizard(self):
        self.ensure_one()
        self._check_state(('running', 'expired'), self.env._("terminate"))
        self._check_manager(self.env._("terminate"))
        return {
            'type': 'ir.actions.act_window',
            'name': self.env._("Terminate %(contract)s", contract=self.name),
            'res_model': 'property.rental.contract.terminate',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_contract_id': self.id},
        }

    def _renew(self, date_start, date_end, rent_amount):
        """ Create the draft renewal of a running or expired contract. """
        self.ensure_one()
        self._check_state(('running', 'expired'), self.env._("renew"))
        return self.create({
            'renewed_from_id': self.id,
            'property_id': self.property_id.id,
            'tenant_id': self.tenant_id.id,
            'user_id': self.user_id.id,
            'company_id': self.company_id.id,
            'date_start': date_start,
            'date_end': date_end,
            'rent_period': self.rent_period,
            'rent_amount': rent_amount,
            'deposit_amount': self.deposit_amount,
            'note': self.note,
        })

    def _terminate(self, date_terminated, reason, note=False):
        self.ensure_one()
        self._check_state(('running', 'expired'), self.env._("terminate"))
        self._check_manager(self.env._("terminate"))
        if not (self.date_start <= date_terminated <= self.date_end):
            raise UserError(self.env._(
                "The termination date must fall within the contract period (%(start)s to %(end)s).",
                start=self.date_start, end=self.date_end,
            ))
        self.write({
            'state': 'terminated',
            'date_terminated': date_terminated,
            'termination_reason': reason,
            'termination_note': note,
        })
        self.renewal_ids.filtered(lambda c: c.state in ('draft', 'approved')).action_cancel()
        self.sudo()._trim_rent_schedule(date_terminated)
        self._release_property()

    # ------------------------------------------------------------------
    # Billing schedule and invoicing
    # ------------------------------------------------------------------
    def _generate_rent_schedule(self):
        """ Create the billing periods of the lease, one per payment period from the start date.
        The last period is shortened to the end date and its rent prorated by day. """
        for contract in self:
            if contract.rent_schedule_ids:
                continue
            step = PERIOD_MONTHS[contract.rent_period]
            first = contract.invoice_from or contract.date_start
            vals_list = []
            index = 0
            while True:
                start = contract.date_start + relativedelta(months=step * index)
                if start > contract.date_end:
                    break
                end = min(start + relativedelta(months=step, days=-1), contract.date_end)
                index += 1
                if start < first:
                    continue
                vals_list.append({
                    'contract_id': contract.id,
                    'period_start': start,
                    'period_end': end,
                    'date_due': start,
                    'amount': contract.currency_id.round(contract.rent_amount * months_between(start, end)),
                })
            self.env['property.rent.schedule'].create(vals_list)

    def _trim_rent_schedule(self, end_date):
        """ After an early end, drop the periods after it and prorate the period it falls in.
        Periods already invoiced are left alone: the accountant credits them if needed. """
        for contract in self:
            lines = contract.rent_schedule_ids
            later = lines.filtered(lambda l: l.period_start > end_date)
            spanning = lines.filtered(lambda l: l.period_start <= end_date < l.period_end)
            invoiced_after = (later | spanning).filtered(lambda l: l.state != 'pending')
            later.filtered(lambda l: l.state == 'pending').unlink()
            for line in spanning.filtered(lambda l: l.state == 'pending'):
                line.write({
                    'period_end': end_date,
                    'amount': contract.currency_id.round(contract.rent_amount * months_between(line.period_start, end_date)),
                })
            if invoiced_after.filtered(lambda l: l.state in ('draft', 'invoiced', 'paid')):
                contract.message_post(body=self.env._(
                    "The lease ended on %(date)s, but these periods are already invoiced past that date: %(periods)s. "
                    "Credit them in Invoicing if they should not be charged.",
                    date=end_date, periods=", ".join(invoiced_after.mapped('display_name')),
                ))

    def action_generate_rent_schedule(self):
        """ Create the billing schedule of a lease started before rent invoicing was available. """
        self._check_state(('running', 'expired'), self.env._("create the billing schedule of"))
        self._check_manager(self.env._("create the billing schedule of"))
        if any(contract.rent_schedule_ids for contract in self):
            raise UserError(self.env._("This contract already has a billing schedule."))
        self.sudo()._generate_rent_schedule()

    def _check_billing_rights(self):
        self.check_access('read')
        if not self.env.user.has_group(BILLING_GROUP):
            raise AccessError(self.env._("You need Invoicing access to do this."))

    def action_create_due_invoices(self):
        """ Invoice the periods of this lease that are due now, as the daily job would. """
        self._check_billing_rights()
        lines = self.env['property.rent.schedule']._get_due_lines(self)
        if not lines:
            raise UserError(self.env._("No rent period of %(contract)s is due for invoicing.", contract=", ".join(self.mapped('name'))))
        lines._create_invoices()
        return self.action_view_invoices() if len(self) == 1 else True

    def action_invoice_deposit(self):
        self.ensure_one()
        self._check_billing_rights()
        if self.state not in ('approved', 'running'):
            raise UserError(self.env._("The deposit is invoiced once the contract is approved or running."))
        if self.currency_id.is_zero(self.deposit_amount):
            raise UserError(self.env._("%(contract)s has no security deposit.", contract=self.name))
        active = self.rental_move_ids.filtered(
            lambda m: m.property_rental_move_kind == 'deposit' and m.move_type == 'out_invoice'
            and m.state != 'cancel' and m.payment_state != 'reversed'
        )
        if active:
            raise UserError(self.env._("The deposit of %(contract)s is already invoiced.", contract=self.name))
        company = self.company_id
        vals = {
            'move_type': 'out_invoice',
            'partner_id': self.tenant_id.id,
            'company_id': company.id,
            'currency_id': self.currency_id.id,
            'invoice_origin': self.name,
            'property_rental_contract_id': self.id,
            'property_id': self.property_id.id,
            'property_rental_move_kind': 'deposit',
            'invoice_line_ids': [Command.create({
                'product_id': company._get_rental_product('deposit').id,
                'name': self.env._("Security deposit for %(property)s, lease %(contract)s",
                                   property=self.property_id.display_name, contract=self.name),
                'quantity': 1,
                'price_unit': self.deposit_amount,
            })],
        }
        if company.rental_journal_id:
            vals['journal_id'] = company.rental_journal_id.id
        move = self.env['account.move'].with_company(company).create(vals)
        if company.rental_auto_post_invoices:
            move.action_post()
        action = self.env['ir.actions.act_window']._for_xml_id('account.action_move_out_invoice_type')
        action.update({'views': [(False, 'form')], 'res_id': move.id, 'domain': [('id', '=', move.id)]})
        return action

    def action_open_deposit_settlement(self):
        self.ensure_one()
        self._check_billing_rights()
        if self.state not in ('expired', 'terminated', 'closed'):
            raise UserError(self.env._("The deposit is settled once the lease has ended."))
        if self.rental_move_ids.filtered(
            lambda m: m.property_rental_move_kind == 'deposit_settlement' and m.state == 'draft'
        ):
            raise UserError(self.env._("A draft deposit settlement already exists: post or delete it first."))
        if self.currency_id.compare_amounts(self.deposit_held, 0.0) <= 0:
            raise UserError(self.env._("No collected deposit is held for %(contract)s.", contract=self.name))
        return {
            'type': 'ir.actions.act_window',
            'name': self.env._("Settle Deposit of %(contract)s", contract=self.name),
            'res_model': 'property.deposit.settlement',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_contract_id': self.id},
        }

    def action_view_invoices(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('account.action_move_out_invoice_type')
        action['domain'] = [('property_rental_contract_id', '=', self.id)]
        action['context'] = {'default_move_type': 'out_invoice', 'create': False}
        return action

    def action_view_payments(self):
        self.ensure_one()
        payments = self.rental_move_ids.filtered(lambda m: m.state == 'posted')._get_reconciled_payments()
        action = self.env['ir.actions.act_window']._for_xml_id('account.action_account_payments')
        action['domain'] = [('id', 'in', payments.ids)]
        action['context'] = {'create': False}
        return action

    # ------------------------------------------------------------------
    # Scheduled action
    # ------------------------------------------------------------------
    @api.model
    def _cron_update_lease_status(self):
        today = fields.Date.context_today(self)
        ended = self.search([('state', '=', 'running'), ('date_end', '<', today)])
        taken_over = ended.filtered(lambda c: c.renewal_ids.filtered(lambda r: r.state == 'running'))
        taken_over._close()
        (ended - taken_over).write({'state': 'expired'})

        activity_type = self.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)
        for company in self.env['res.company'].search([]):
            notice = company.rental_expiry_notice_days
            if not notice or not activity_type:
                continue
            expiring = self.search([
                ('company_id', '=', company.id),
                ('state', '=', 'running'),
                ('date_end', '>=', today),
                ('date_end', '<=', today + relativedelta(days=notice)),
                ('renewal_ids', '=', False),
            ])
            for contract in expiring:
                already = contract.activity_ids.filtered(
                    lambda a: a.activity_type_id == activity_type and a.summary == contract._expiry_activity_summary()
                )
                if not already:
                    contract.activity_schedule(
                        'mail.mail_activity_data_todo',
                        date_deadline=contract.date_end - relativedelta(days=min(notice, 7)),
                        summary=contract._expiry_activity_summary(),
                        note=self.env._("Renew, close or terminate this lease before %(date)s.", date=contract.date_end),
                        user_id=contract.user_id.id or self.env.user.id,
                    )

    def _expiry_activity_summary(self):
        return self.env._("Lease %(contract)s ends on %(date)s", contract=self.name, date=self.date_end)

    # ------------------------------------------------------------------
    # Smart buttons
    # ------------------------------------------------------------------
    def action_view_documents(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': self.env._("Contract Documents"),
            'res_model': 'ir.attachment',
            'view_mode': 'kanban,list,form',
            'domain': [('res_model', '=', self._name), ('res_id', '=', self.id)],
            'context': {'default_res_model': self._name, 'default_res_id': self.id},
        }

    def action_view_lead(self):
        self.ensure_one()
        return {'type': 'ir.actions.act_window', 'res_model': 'crm.lead', 'view_mode': 'form', 'res_id': self.lead_id.id}

    def action_view_renewal(self):
        self.ensure_one()
        target = self.renewal_id
        return {'type': 'ir.actions.act_window', 'res_model': self._name, 'view_mode': 'form', 'res_id': target.id}

    def action_view_previous(self):
        self.ensure_one()
        return {'type': 'ir.actions.act_window', 'res_model': self._name, 'view_mode': 'form',
                'res_id': self.renewed_from_id.id}
