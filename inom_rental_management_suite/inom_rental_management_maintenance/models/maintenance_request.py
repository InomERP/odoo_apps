from odoo import Command, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError

AGENT_GROUP = 'inom_rental_management.group_rental_agent'
MANAGER_GROUP = 'inom_rental_management.group_rental_manager'
MAINTENANCE_MANAGER_GROUP = 'maintenance.group_equipment_manager'
BILLING_GROUP = 'account.group_account_invoice'
COST_FIELDS = ('maintenance_cost', 'cost_charged_to')


class MaintenanceRequest(models.Model):
    _inherit = 'maintenance.request'

    property_id = fields.Many2one(
        'property.property', string='Property', index='btree_not_null', tracking=True, check_company=True,
        ondelete='restrict',
    )
    rental_contract_id = fields.Many2one(
        'property.rental.contract', string='Rental Contract', index='btree_not_null', tracking=True,
        check_company=True, ondelete='restrict',
        domain="[('property_id', '=', property_id), ('state', 'in', ('running', 'expired', 'approved'))]",
    )
    tenant_id = fields.Many2one(related='rental_contract_id.tenant_id', store=True, string='Tenant')
    property_owner_id = fields.Many2one(related='property_id.owner_id', string='Owner')
    currency_id = fields.Many2one(related='company_id.currency_id')
    maintenance_cost = fields.Monetary(
        string='Cost', tracking=True, help="Cost of the work, for reporting and for charging it on.",
    )
    cost_charged_to = fields.Selection(
        selection=[('company', 'Company'), ('owner', 'Owner'), ('tenant', 'Tenant')],
        string='Cost Borne By', default='company', required=True, tracking=True,
    )
    schedule_reminder_date = fields.Datetime(
        copy=False, readonly=True, help="Scheduled date for which the responsible person was last reminded.",
    )
    recharge_move_ids = fields.One2many('account.move', 'maintenance_request_id', string='Recharge Invoices')
    recharge_move_count = fields.Integer(compute='_compute_recharge_move_count', compute_sudo=True)

    _maintenance_cost_positive = models.Constraint(
        'CHECK(maintenance_cost >= 0)',
        'The maintenance cost cannot be negative.',
    )

    def _compute_recharge_move_count(self):
        for request in self:
            request.recharge_move_count = len(request.recharge_move_ids.filtered(lambda m: m.state != 'cancel'))

    @api.onchange('property_id')
    def _onchange_property_id_rental(self):
        prop = self.property_id
        if self.rental_contract_id.property_id != prop:
            self.rental_contract_id = False
        if prop:
            if prop.maintenance_team_id:
                self.maintenance_team_id = prop.maintenance_team_id
            if prop.technician_user_id and not self.user_id:
                self.user_id = prop.technician_user_id
            running = prop.rental_contract_ids.filtered(lambda c: c.state in ('running', 'expired'))[:1]
            if running and not self.rental_contract_id:
                self.rental_contract_id = running

    @api.constrains('property_id', 'rental_contract_id', 'cost_charged_to')
    def _check_property_links(self):
        for request in self:
            contract = request.rental_contract_id
            if contract and contract.property_id != request.property_id:
                raise ValidationError(self.env._(
                    "Rental contract %(contract)s is for %(contract_property)s, not for %(property)s.",
                    contract=contract.name, contract_property=contract.property_id.display_name,
                    property=request.property_id.display_name or self.env._("no property"),
                ))
            if request.cost_charged_to == 'tenant' and not contract:
                raise ValidationError(self.env._("Link the rental contract before charging the cost to the tenant."))
            if request.cost_charged_to == 'owner' and not request.property_id.owner_id:
                raise ValidationError(self.env._("The property has no owner to charge the cost to."))

    # ------------------------------------------------------------------
    # Access
    # ------------------------------------------------------------------
    def _check_property_rights(self, vals):
        """ Only Real Estate users (or maintenance managers) may link a request to a property or lease,
        only managers may set costs, and nobody may move a request to a done stage unassigned. """
        user = self.env.user
        if self.env.su:
            return
        if (vals.get('property_id') or vals.get('rental_contract_id')) \
                and not (user.has_group(AGENT_GROUP) or user.has_group(MAINTENANCE_MANAGER_GROUP)):
            raise AccessError(self.env._("Only Real Estate users can link maintenance requests to properties."))
        if any(f in vals for f in COST_FIELDS) and not (user.has_group(MANAGER_GROUP) or user.has_group(MAINTENANCE_MANAGER_GROUP)):
            default_cost = not vals.get('maintenance_cost') and vals.get('cost_charged_to', 'company') == 'company'
            if not default_cost:
                raise AccessError(self.env._("Only Property Managers or Maintenance Managers can set maintenance costs."))

    def _check_assigned_when_done(self):
        for request in self:
            if request.property_id and request.stage_id.done and not request.user_id:
                raise UserError(self.env._(
                    "Assign a responsible person to %(request)s before closing it.", request=request.name,
                ))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._check_property_rights(vals)
        requests = super().create(vals_list)
        requests._check_assigned_when_done()
        return requests

    def write(self, vals):
        self._check_property_rights(vals)
        if any(f in vals for f in COST_FIELDS) and self.sudo().recharge_move_ids.filtered(lambda m: m.state != 'cancel'):
            raise UserError(self.env._("The cost was already invoiced: cancel the recharge invoice before changing it."))
        result = super().write(vals)
        if 'stage_id' in vals or 'user_id' in vals:
            self._check_assigned_when_done()
        return result

    @api.ondelete(at_uninstall=False)
    def _unlink_keep_property_history(self):
        """ Property maintenance is history: only untouched new requests can be deleted. """
        first_stage = self.env['maintenance.stage'].search([], order='sequence, id', limit=1)
        for request in self.filtered('property_id'):
            if request.stage_id != first_stage or request.recharge_move_ids:
                raise UserError(self.env._(
                    "%(request)s is part of the property's maintenance history: archive it instead of deleting it.",
                    request=request.name,
                ))

    # ------------------------------------------------------------------
    # Cost recharge
    # ------------------------------------------------------------------
    def action_charge_cost(self):
        """ Invoice the cost to the tenant or the owner with a standard customer invoice. """
        self.ensure_one()
        self.check_access('read')
        if not self.env.user.has_group(BILLING_GROUP):
            raise AccessError(self.env._("You need Invoicing access to charge maintenance costs."))
        if self.cost_charged_to == 'company':
            raise UserError(self.env._("The cost is borne by the company: there is nobody to invoice."))
        if self.currency_id.is_zero(self.maintenance_cost):
            raise UserError(self.env._("Enter the cost before charging it."))
        if self.recharge_move_ids.filtered(lambda m: m.state != 'cancel'):
            raise UserError(self.env._("This maintenance cost is already invoiced."))
        partner = self.tenant_id if self.cost_charged_to == 'tenant' else self.property_id.owner_id
        product = self.company_id._get_rental_maintenance_product()
        invoice = self.env['account.move'].with_company(self.company_id).create({
            'move_type': 'out_invoice',
            'partner_id': partner.id,
            'company_id': self.company_id.id,
            'invoice_origin': self.name,
            'maintenance_request_id': self.id,
            'property_id': self.property_id.id,
            'property_rental_contract_id': self.rental_contract_id.id,
            'invoice_line_ids': [Command.create({
                'product_id': product.id,
                'name': self.env._("Maintenance: %(request)s (%(property)s)",
                                   request=self.name, property=self.property_id.display_name),
                'quantity': 1,
                'price_unit': self.maintenance_cost,
            })],
        })
        action = self.env['ir.actions.act_window']._for_xml_id('account.action_move_out_invoice_type')
        action.update({'views': [(False, 'form')], 'res_id': invoice.id, 'domain': [('id', '=', invoice.id)]})
        return action

    def action_view_recharge_invoices(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('account.action_move_out_invoice_type')
        action['domain'] = [('maintenance_request_id', '=', self.id)]
        action['context'] = {'create': False}
        return action
