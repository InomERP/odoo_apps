from odoo import models, fields

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    max_discount_limit = fields.Float(
        string="Maximum Allowed Discount (%)",
        config_parameter='purchase_global_discount.max_discount_limit'
    )

    max_discount_amount = fields.Float(
        string="Maximum Discount Amount",
        config_parameter='purchase_global_discount.max_discount_amount'
    )