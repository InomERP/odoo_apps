from odoo import models, fields

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    max_discount_limit = fields.Float(
        string="Maximum Allowed Discount (%)",
        config_parameter='sale_global_discount_approval.max_discount_limit'
    )

    max_discount_amount = fields.Float(
        string="Maximum Discount Amount",
        config_parameter='sale_global_discount_approval.max_discount_amount'
    )

    discount_account_id = fields.Many2one(
        'account.account',
        string="Discount Account",
        config_parameter='sale_global_discount_approval.discount_account_id'
    )
    

# from odoo import models, fields, api
# from odoo.exceptions import ValidationError


# class ResConfigSettings(models.TransientModel):
#     _inherit = 'res.config.settings'

#     max_discount_limit = fields.Float(
#         string="Maximum Allowed Discount (%)",
#         config_parameter='sale_global_discount_approval.max_discount_limit'
#     )

#     discount_account_id = fields.Many2one(
#         'account.account',
#         string="Discount Account",
#         config_parameter='sale_global_discount_approval.discount_account_id'
#     )




