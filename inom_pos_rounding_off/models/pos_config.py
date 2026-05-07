from odoo import models, fields, api
from odoo.exceptions import ValidationError


class PosConfig(models.Model):
    _inherit = 'pos.config'

    is_rounding_enabled = fields.Boolean(
        string='Enable Rounding Off',
        default=False,
    )

    rounding_type = fields.Selection(
        selection=[
            ('manual', 'Manual'),
            ('automatic', 'Automatic'),
        ],
        string='Rounding Type',
        default='manual',
    )

    rounding_precision = fields.Float(
        string='Rounding Precision',
        default=0.05,
        digits=(16, 2),
    )

    rounding_payment_method_id = fields.Many2one(
        comodel_name='pos.payment.method',
        string='Rounding Payment Method',
        domain=[('is_rounding_method', '=', True)],
    )

    rounding_account_id = fields.Many2one(
        comodel_name='account.account',
        string='Rounding Account',
    )

    @api.constrains('rounding_precision')
    def _check_rounding_precision(self):
        for rec in self:
            if rec.is_rounding_enabled and rec.rounding_precision <= 0:
                raise ValidationError(
                    "Rounding Precision 0 se zyada honi chahiye!"
                )

    @api.onchange('is_rounding_enabled')
    def _onchange_rounding_enabled(self):
        if not self.is_rounding_enabled:
            self.rounding_type = 'manual'
            self.rounding_payment_method_id = False
            self.rounding_account_id = False

    def _get_pos_ui_pos_config(self, params):
        config_data = super()._get_pos_ui_pos_config(params)
        config_data.update({
            'is_rounding_enabled': self.is_rounding_enabled,
            'rounding_type': self.rounding_type,
            'rounding_precision': self.rounding_precision,
            'rounding_payment_method_id': (
                self.rounding_payment_method_id.id
                if self.rounding_payment_method_id else False
            ),
            'rounding_account_id': (
                self.rounding_account_id.id
                if self.rounding_account_id else False
            ),
        })
        return config_data