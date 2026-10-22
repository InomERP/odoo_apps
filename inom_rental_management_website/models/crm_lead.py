from dateutil.relativedelta import relativedelta

from odoo import fields, models

LEASE_MONTHS = (6, 11, 12, 24, 36)


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    # Details of rent and purchase requests sent from a property page
    property_move_in_date = fields.Date(string='Preferred Move-in Date')
    property_lease_months = fields.Integer(string='Lease Length (Months)')
    property_occupants = fields.Integer(string='Occupants')
    property_financing = fields.Selection(
        selection=[('cash', 'Own Funds'), ('loan', 'Home Loan'), ('undecided', 'Not Decided Yet')],
        string='Financing',
    )
    property_purchase_timeline = fields.Selection(
        selection=[('now', 'Immediately'), ('1_3', 'Within 1-3 Months'), ('3_6', 'Within 3-6 Months'),
                   ('later', 'Later')],
        string='Purchase Timeline',
    )

    _property_lease_months_range = models.Constraint(
        'CHECK(property_lease_months >= 0 AND property_lease_months <= 120)',
        'The lease length must be between 0 and 120 months.',
    )
    _property_occupants_range = models.Constraint(
        'CHECK(property_occupants >= 0 AND property_occupants <= 50)',
        'The number of occupants must be between 0 and 50.',
    )

    def action_create_property_rental(self):
        """ Start the draft lease on the requested move-in date, for the requested length. """
        action = super().action_create_property_rental()
        if self.property_move_in_date or self.property_lease_months:
            contract = self.env['property.rental.contract'].browse(action['res_id'])
            today = fields.Date.context_today(self)
            start = max(self.property_move_in_date or today, today)
            months = self.property_lease_months or 12
            contract.write({'date_start': start, 'date_end': start + relativedelta(months=months, days=-1)})
        return action
