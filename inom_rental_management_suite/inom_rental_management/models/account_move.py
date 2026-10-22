from odoo import fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    # The links are copied, so that credit notes created by reversal stay linked to their sale or lease.
    property_sale_contract_id = fields.Many2one(
        'property.sale.contract', string='Property Sale', index='btree_not_null',
        ondelete='restrict', readonly=True, check_company=True,
    )
    property_id = fields.Many2one(
        'property.property', string='Property', index='btree_not_null',
        ondelete='restrict', readonly=True, check_company=True,
    )
    property_rental_contract_id = fields.Many2one(
        'property.rental.contract', string='Rental Contract', index='btree_not_null',
        ondelete='restrict', readonly=True, check_company=True,
    )
    property_rent_schedule_id = fields.Many2one(
        'property.rent.schedule', string='Rental Period', index='btree_not_null',
        ondelete='restrict', readonly=True,
    )
    property_rental_move_kind = fields.Selection(
        selection=[
            ('rent', 'Rent'),
            ('deposit', 'Security Deposit'),
            ('deposit_settlement', 'Deposit Settlement'),
        ],
        string='Rental Document', readonly=True, index='btree_not_null',
    )

    rental_overdue_notified = fields.Boolean(copy=False, readonly=True)

    # One live invoice per rental period, and one live deposit invoice per lease, enforced by the database.
    _property_rent_period_uniq = models.UniqueIndex(
        "(property_rent_schedule_id) WHERE property_rent_schedule_id IS NOT NULL "
        "AND move_type = 'out_invoice' AND state != 'cancel' AND payment_state IS DISTINCT FROM 'reversed'",
        'This rental period is already invoiced.',
    )
    _property_rental_deposit_uniq = models.UniqueIndex(
        "(property_rental_contract_id) WHERE property_rental_move_kind = 'deposit' "
        "AND move_type = 'out_invoice' AND state != 'cancel' AND payment_state IS DISTINCT FROM 'reversed'",
        'The deposit of this rental contract is already invoiced.',
    )
