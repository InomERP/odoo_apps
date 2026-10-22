from odoo import Command, api, fields, models
from odoo.exceptions import UserError, ValidationError

LOCKED_AFTER_DRAFT = ('property_id', 'buyer_id', 'sale_price', 'booking_amount', 'company_id')


class PropertySaleContract(models.Model):
    _name = 'property.sale.contract'
    _description = 'Property Sale Contract'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'booking_date desc, id desc'
    _check_company_auto = True

    name = fields.Char(string='Reference', required=True, readonly=True, copy=False, default='/')
    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('booked', 'Booked'),
            ('sold', 'Sold'),
            ('cancelled', 'Cancelled'),
        ],
        required=True, default='draft', copy=False, tracking=True,
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
        domain="[('property_for', '=', 'sale'), ('state', 'in', ('draft', 'available'))]",
    )
    owner_id = fields.Many2one(related='property_id.owner_id', store=True, string='Owner')
    buyer_id = fields.Many2one(
        'res.partner', string='Buyer', required=True, tracking=True, check_company=True,
        index=True, ondelete='restrict',
        domain="[('is_property_buyer', '=', True)]",
    )
    lead_id = fields.Many2one(
        'crm.lead', string='Enquiry', index='btree_not_null', ondelete='set null', copy=False,
        check_company=True,
    )
    booking_date = fields.Date(required=True, tracking=True, default=fields.Date.context_today)
    date_sold = fields.Date(string='Sold On', readonly=True, copy=False, tracking=True)
    sale_price = fields.Monetary(
        string='Agreed Sale Price', tracking=True,
        compute='_compute_sale_price', store=True, readonly=False, precompute=True,
    )
    booking_amount = fields.Monetary(tracking=True)
    payment_term_id = fields.Many2one(
        'account.payment.term', string='Balance Payment Terms', check_company=True,
        help="Payment terms of the balance invoice. Use a term with several lines to collect the balance in instalments.",
    )
    property_state_before_booking = fields.Char(copy=False, readonly=True)
    note = fields.Html(string='Terms and Conditions')

    invoice_ids = fields.One2many(
        'account.move', 'property_sale_contract_id', string='Invoices',
        groups='account.group_account_invoice',
    )
    invoice_count = fields.Integer(compute='_compute_invoice_count', compute_sudo=True)
    amount_invoiced = fields.Monetary(
        compute='_compute_invoice_amounts', store=True,
        help="Untaxed amount of posted invoices, less posted credit notes.",
    )
    amount_paid = fields.Monetary(compute='_compute_invoice_amounts', store=True)
    amount_due = fields.Monetary(compute='_compute_invoice_amounts', store=True)
    invoice_status = fields.Selection(
        selection=[
            ('not_invoiced', 'Not Invoiced'),
            ('partial', 'Partially Invoiced'),
            ('invoiced', 'Fully Invoiced'),
            ('paid', 'Paid'),
        ],
        compute='_compute_invoice_amounts', store=True,
    )
    document_count = fields.Integer(compute='_compute_document_count')

    _sale_price_positive = models.Constraint(
        'CHECK(sale_price >= 0)',
        'The sale price cannot be negative.',
    )
    _booking_amount_positive = models.Constraint(
        'CHECK(booking_amount >= 0)',
        'The booking amount cannot be negative.',
    )

    @api.depends('property_id')
    def _compute_sale_price(self):
        for contract in self:
            contract.sale_price = contract.property_id.sale_price

    def _compute_invoice_count(self):
        for contract in self:
            contract.invoice_count = len(contract.invoice_ids)

    @api.depends(
        'sale_price', 'invoice_ids.state', 'invoice_ids.amount_untaxed_signed',
        'invoice_ids.amount_total_signed', 'invoice_ids.amount_residual_signed',
    )
    def _compute_invoice_amounts(self):
        for contract in self:
            posted = contract.invoice_ids.filtered(lambda m: m.state == 'posted')
            invoiced = sum(posted.mapped('amount_untaxed_signed'))
            total = sum(posted.mapped('amount_total_signed'))
            due = sum(posted.mapped('amount_residual_signed'))
            contract.amount_invoiced = invoiced
            contract.amount_due = due
            contract.amount_paid = total - due
            currency = contract.currency_id
            if not posted or currency.is_zero(invoiced):
                contract.invoice_status = 'not_invoiced'
            elif currency.compare_amounts(invoiced, contract.sale_price) < 0:
                contract.invoice_status = 'partial'
            elif currency.is_zero(due):
                contract.invoice_status = 'paid'
            else:
                contract.invoice_status = 'invoiced'

    def _compute_document_count(self):
        counts = dict(self.env['ir.attachment']._read_group(
            [('res_model', '=', self._name), ('res_id', 'in', self.ids)],
            groupby=['res_id'], aggregates=['__count'],
        ))
        for contract in self:
            contract.document_count = counts.get(contract.id, 0)

    @api.constrains('buyer_id', 'property_id')
    def _check_buyer(self):
        for contract in self:
            buyer = contract.buyer_id
            if not buyer.is_property_buyer:
                raise ValidationError(self.env._(
                    "%(partner)s is not marked as a Property Buyer.", partner=buyer.display_name,
                ))
            owner = contract.property_id.owner_id
            if owner and buyer.commercial_partner_id == owner.commercial_partner_id:
                raise ValidationError(self.env._(
                    "%(partner)s already owns %(property)s and cannot buy it.",
                    partner=buyer.display_name, property=contract.property_id.display_name,
                ))

    @api.constrains('property_id')
    def _check_property_for_sale(self):
        for contract in self:
            if contract.property_id.property_for != 'sale':
                raise ValidationError(self.env._(
                    "%(property)s is not offered for sale.", property=contract.property_id.display_name,
                ))

    @api.constrains('booking_amount', 'sale_price')
    def _check_booking_amount(self):
        for contract in self:
            if contract.currency_id.compare_amounts(contract.booking_amount, contract.sale_price) > 0:
                raise ValidationError(self.env._("The booking amount cannot exceed the agreed sale price."))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', '/') == '/':
                company = self.env['res.company'].browse(vals.get('company_id')) or self.env.company
                vals['name'] = self.env['ir.sequence'].with_company(company).next_by_code('property.sale.contract') or '/'
        return super().create(vals_list)

    def write(self, vals):
        locked = set(LOCKED_AFTER_DRAFT) & set(vals)
        if locked and any(contract.state != 'draft' for contract in self):
            raise UserError(self.env._(
                "The property, buyer, prices and company of a sale cannot be changed once it is booked. "
                "Cancel the sale and create a new one instead."
            ))
        return super().write(vals)

    # ------------------------------------------------------------------
    # Status transitions
    # ------------------------------------------------------------------
    def _check_state(self, allowed, action, operation='write'):
        # Check rights before any side effect on invoices or the property.
        # Invoicing only needs to read the sale; the invoice itself is checked by accounting rights.
        self.check_access(operation)
        for contract in self:
            if contract.state not in allowed:
                raise UserError(self.env._(
                    "%(contract)s is %(state)s: you cannot %(action)s it.",
                    contract=contract.name,
                    state=dict(self._fields['state']._description_selection(self.env))[contract.state],
                    action=action,
                ))

    def action_book(self):
        self._check_state(('draft',), self.env._("book"))
        for contract in self:
            prop = contract.property_id
            # Lock the property row so two users cannot book it at the same time.
            self.env.cr.execute('SELECT id FROM property_property WHERE id = %s FOR UPDATE', [prop.id])
            if prop.state not in ('draft', 'available'):
                raise UserError(self.env._(
                    "%(property)s is %(state)s and cannot be booked.",
                    property=prop.display_name,
                    state=dict(prop._fields['state']._description_selection(self.env))[prop.state],
                ))
            if contract.currency_id.is_zero(contract.sale_price):
                raise UserError(self.env._("Set the agreed sale price before booking %(contract)s.", contract=contract.name))
            conflicting = self.sudo().search([
                ('id', '!=', contract.id), ('property_id', '=', prop.id), ('state', 'in', ('booked', 'sold')),
            ], limit=1)
            if conflicting:
                raise UserError(self.env._(
                    "%(property)s is already booked or sold under %(contract)s.",
                    property=prop.display_name, contract=conflicting.name,
                ))
            contract.write({'state': 'booked', 'property_state_before_booking': prop.state})
            prop.sudo().state = 'booked'

    def action_sell(self):
        self._check_state(('booked',), self.env._("mark as sold"))
        for contract in self:
            if contract.currency_id.compare_amounts(contract.amount_invoiced, contract.sale_price) < 0:
                raise UserError(self.env._(
                    "%(contract)s is not fully invoiced: %(invoiced)s of %(price)s posted. "
                    "Post the balance invoice before marking the property as sold.",
                    contract=contract.name,
                    invoiced=contract.currency_id.format(contract.amount_invoiced),
                    price=contract.currency_id.format(contract.sale_price),
                ))
            contract.write({'state': 'sold', 'date_sold': fields.Date.context_today(self)})
            contract.property_id.sudo().state = 'sold'
            if contract.lead_id.won_status == 'pending':
                contract.lead_id.sudo().action_set_won()

    def action_cancel(self):
        self._check_state(('draft', 'booked'), self.env._("cancel"))
        for contract in self:
            moves = contract.sudo().invoice_ids.filtered(lambda m: m.state != 'cancel')
            if moves and not self.env.user.has_group('account.group_account_invoice'):
                raise UserError(self.env._(
                    "%(contract)s has invoices. Ask someone with Invoicing access to cancel it, "
                    "so the invoices are cancelled or credited.",
                    contract=contract.name,
                ))
            moves.filtered(lambda m: m.state == 'draft').button_cancel()
            to_reverse = moves.filtered(
                lambda m: m.state == 'posted' and m.move_type == 'out_invoice' and not m.reversal_move_ids
            )
            if to_reverse:
                to_reverse._reverse_moves([{
                    'ref': self.env._("Cancellation of %(contract)s", contract=contract.name),
                    'invoice_date': fields.Date.context_today(self),
                } for _move in to_reverse])
            was_booked = contract.state == 'booked'
            contract.state = 'cancelled'
            if was_booked and contract.property_id.state == 'booked':
                contract.property_id.sudo().state = contract.property_state_before_booking or 'available'

    def action_reset_to_draft(self):
        self._check_state(('cancelled',), self.env._("reset to draft"))
        self.write({'state': 'draft', 'property_state_before_booking': False})

    # ------------------------------------------------------------------
    # Invoicing
    # ------------------------------------------------------------------
    def _get_sale_products(self):
        self.ensure_one()
        company = self.company_id
        booking = company.rental_sale_booking_product_id or self.env.ref('inom_rental_management.product_property_booking')
        sale = company.rental_sale_product_id or self.env.ref('inom_rental_management.product_property_sale')
        return booking, sale

    def _invoiced_untaxed_including_drafts(self):
        moves = self.invoice_ids.filtered(lambda m: m.state in ('draft', 'posted'))
        return sum(moves.mapped('amount_untaxed_signed'))

    def _create_invoice(self, product, amount, label, payment_term=False):
        self.ensure_one()
        vals = {
            'move_type': 'out_invoice',
            'partner_id': self.buyer_id.id,
            'company_id': self.company_id.id,
            'currency_id': self.currency_id.id,
            'invoice_origin': self.name,
            'property_sale_contract_id': self.id,
            'property_id': self.property_id.id,
            'invoice_line_ids': [Command.create({
                'product_id': product.id,
                'name': label,
                'quantity': 1,
                'price_unit': amount,
            })],
        }
        if payment_term:
            vals['invoice_payment_term_id'] = payment_term.id
        return self.env['account.move'].with_company(self.company_id).create(vals)

    def _action_open_invoice(self, invoice):
        action = self.env['ir.actions.act_window']._for_xml_id('account.action_move_out_invoice_type')
        action.update({'views': [(False, 'form')], 'res_id': invoice.id, 'domain': [('id', '=', invoice.id)]})
        return action

    def action_create_booking_invoice(self):
        self.ensure_one()
        self._check_state(('booked',), self.env._("invoice the booking amount of"), operation='read')
        if self.currency_id.is_zero(self.booking_amount):
            raise UserError(self.env._("%(contract)s has no booking amount to invoice.", contract=self.name))
        booking_product, _sale_product = self._get_sale_products()
        existing = self.invoice_ids.filtered(
            lambda m: m.state != 'cancel' and m.move_type == 'out_invoice' and booking_product in m.invoice_line_ids.product_id
        )
        if existing:
            raise UserError(self.env._("The booking amount of %(contract)s is already invoiced.", contract=self.name))
        invoice = self._create_invoice(
            booking_product, self.booking_amount,
            self.env._("Booking amount for %(property)s", property=self.property_id.display_name),
        )
        return self._action_open_invoice(invoice)

    def action_create_balance_invoice(self):
        self.ensure_one()
        self._check_state(('booked',), self.env._("invoice the balance of"), operation='read')
        remaining = self.sale_price - self._invoiced_untaxed_including_drafts()
        if self.currency_id.compare_amounts(remaining, 0.0) <= 0:
            raise UserError(self.env._(
                "%(contract)s is already fully invoiced, counting draft invoices.", contract=self.name,
            ))
        _booking_product, sale_product = self._get_sale_products()
        invoice = self._create_invoice(
            sale_product, remaining,
            self.env._("Sale of %(property)s", property=self.property_id.display_name),
            payment_term=self.payment_term_id,
        )
        return self._action_open_invoice(invoice)

    # ------------------------------------------------------------------
    # Smart buttons and reports
    # ------------------------------------------------------------------
    def action_view_invoices(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('account.action_move_out_invoice_type')
        action['domain'] = [('property_sale_contract_id', '=', self.id)]
        action['context'] = {'default_move_type': 'out_invoice', 'create': False}
        return action

    def action_view_documents(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': self.env._("Sale Documents"),
            'res_model': 'ir.attachment',
            'view_mode': 'kanban,list,form',
            'domain': [('res_model', '=', self._name), ('res_id', '=', self.id)],
            'context': {'default_res_model': self._name, 'default_res_id': self.id},
        }

    def action_view_lead(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'crm.lead',
            'view_mode': 'form',
            'res_id': self.lead_id.id,
        }

    def _get_report_invoices(self):
        """ Invoices shown on the sale summary, readable by anyone allowed to print the sale. """
        self.ensure_one()
        return self.sudo().invoice_ids.filtered(lambda m: m.state == 'posted').sorted('invoice_date')
