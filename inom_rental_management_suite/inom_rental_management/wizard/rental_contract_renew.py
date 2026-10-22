from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class PropertyRentalContractRenew(models.TransientModel):
    _name = 'property.rental.contract.renew'
    _description = 'Renew Rental Contract'

    contract_id = fields.Many2one('property.rental.contract', required=True, readonly=True)
    currency_id = fields.Many2one(related='contract_id.currency_id')
    current_rent = fields.Monetary(related='contract_id.rent_amount', string='Current Monthly Rent')
    date_start = fields.Date(
        string='New Start Date', required=True,
        compute='_compute_dates', store=True, readonly=False, precompute=True,
    )
    date_end = fields.Date(
        string='New End Date', required=True,
        compute='_compute_dates', store=True, readonly=False, precompute=True,
    )
    increase_percent = fields.Float(string='Rent Increase (%)', digits=(5, 2))
    rent_amount = fields.Monetary(
        string='New Monthly Rent',
        compute='_compute_rent_amount', store=True, readonly=False, precompute=True,
    )

    @api.depends('contract_id')
    def _compute_dates(self):
        for wizard in self:
            contract = wizard.contract_id
            if not contract:
                continue
            wizard.date_start = contract.date_end + relativedelta(days=1)
            # Same length as the current contract.
            wizard.date_end = wizard.date_start + (contract.date_end - contract.date_start)

    @api.depends('contract_id', 'increase_percent')
    def _compute_rent_amount(self):
        for wizard in self:
            rent = wizard.contract_id.rent_amount * (1 + wizard.increase_percent / 100.0)
            wizard.rent_amount = wizard.currency_id.round(rent) if wizard.currency_id else rent

    @api.constrains('increase_percent', 'rent_amount')
    def _check_amounts(self):
        for wizard in self:
            if wizard.increase_percent <= -100 or wizard.rent_amount < 0:
                raise ValidationError(self.env._("The new rent cannot be negative."))

    def action_renew(self):
        self.ensure_one()
        renewal = self.contract_id._renew(self.date_start, self.date_end, self.rent_amount)
        self.contract_id.message_post(body=self.env._("Renewed by %(renewal)s.", renewal=renewal._get_html_link()))
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'property.rental.contract',
            'view_mode': 'form',
            'res_id': renewal.id,
        }
