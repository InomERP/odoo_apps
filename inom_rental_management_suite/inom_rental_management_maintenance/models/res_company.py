from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    rental_maintenance_reminder_days = fields.Integer(
        string='Maintenance Reminder (Days)', default=1,
        help="Remind the responsible person of property maintenance scheduled within this many days. 0 disables it.",
    )
    rental_maintenance_product_id = fields.Many2one(
        'product.product', string='Maintenance Recharge Product',
        help="Product used to invoice maintenance costs to a tenant or owner. Its taxes and income account apply.",
    )

    def _get_rental_maintenance_product(self):
        self.ensure_one()
        return self.rental_maintenance_product_id \
            or self.env.ref('inom_rental_management_maintenance.product_maintenance_recharge', raise_if_not_found=False) \
            or self.env['product.product']
