from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    rental_maintenance_reminder_days = fields.Integer(
        related='company_id.rental_maintenance_reminder_days', readonly=False,
    )
    rental_maintenance_product_id = fields.Many2one(
        related='company_id.rental_maintenance_product_id', readonly=False,
    )
