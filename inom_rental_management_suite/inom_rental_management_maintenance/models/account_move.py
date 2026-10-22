from odoo import fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    maintenance_request_id = fields.Many2one(
        'maintenance.request', string='Maintenance Request', index='btree_not_null',
        ondelete='restrict', readonly=True,
    )
