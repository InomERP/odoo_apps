from odoo import Command, models, fields, api
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
                    self.env._("Rounding Precision 0 se zyada honi chahiye!")
                )

    @api.onchange('is_rounding_enabled')
    def _onchange_rounding_enabled(self):
        if not self.is_rounding_enabled:
            self.rounding_type = 'manual'
            self.rounding_payment_method_id = False
            self.rounding_account_id = False

    @api.model_create_multi
    def create(self, vals_list):
        configs = super().create(vals_list)
        configs._add_rounding_payment_method()
        return configs

    def write(self, vals):
        res = super().write(vals)
        if {'is_rounding_enabled', 'rounding_payment_method_id', 'payment_method_ids'} & vals.keys():
            self._add_rounding_payment_method()
        return res

    def _add_rounding_payment_method(self):
        # The POS only uses payment methods linked to the shop, so the
        # rounding method must be part of it for rounding to work.
        for config in self:
            method = config.rounding_payment_method_id
            if config.is_rounding_enabled and method and method not in config.payment_method_ids:
                config.payment_method_ids = [Command.set((config.payment_method_ids | method).ids)]

    @api.model
    def _link_rounding_payment_methods(self):
        """Called on install/upgrade to fix shops configured before the auto-link."""
        self.search([('is_rounding_enabled', '=', True)])._add_rounding_payment_method()
