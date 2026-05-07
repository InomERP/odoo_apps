from odoo import models, fields


class PosPaymentMethod(models.Model):
    _inherit = 'pos.payment.method'

    is_rounding_method = fields.Boolean(
        string='Is Rounding Method?',
        default=False,
    )

    is_auto_rounding = fields.Boolean(
        string='Auto Apply Rounding On Select?',
        default=False,
    )