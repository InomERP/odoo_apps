from odoo import models, fields

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    pos_is_rounding_enabled = fields.Boolean(
        string='Enable Rounding Off',
        related='pos_config_id.is_rounding_enabled',
        readonly=False,
    )
    pos_rounding_type = fields.Selection(
        selection=[('manual','Manual'),('automatic','Automatic')],
        string='Rounding Type',
        related='pos_config_id.rounding_type',
        readonly=False,
    )
    pos_rounding_precision = fields.Float(
        string='Rounding Precision',
        related='pos_config_id.rounding_precision',
        readonly=False,
    )
    pos_rounding_payment_method_id = fields.Many2one(
        comodel_name='pos.payment.method',
        related='pos_config_id.rounding_payment_method_id',
        readonly=False,
    )
    pos_rounding_account_id = fields.Many2one(
        comodel_name='account.account',
        related='pos_config_id.rounding_account_id',
        readonly=False,
    )