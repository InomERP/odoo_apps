from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    enable_overdue_interest = fields.Boolean(
        string='Interest on Overdue Invoices',
        config_parameter='inom_interest.enable_overdue_interest'
    )

    auto_compute_interest = fields.Boolean(
        string='Auto-Compute Interest',
        config_parameter='inom_interest.auto_compute_interest'
    )

    auto_apply_interest = fields.Boolean(
        string='Auto-Apply Interest',
        config_parameter='inom_interest.auto_apply_interest'
    )

    overdue_output_type = fields.Selection([
        ('journal_entry', 'Journal Entry'),
        ('debit_note', 'Debit Note'),
    ],
        string='Default Output Type',
        config_parameter='inom_interest.overdue_output_type',
        default='debit_note'
    )


    interest_rule_id = fields.Many2one(
        'overdue.interest.rule',
        string='Default Interest Rule'
    )

    interest_account_id = fields.Many2one(
        'account.account',
        string='Interest Income Account'
    )

    interest_journal_id = fields.Many2one(
        'account.journal',
        string='Interest Journal'
    )

    interest_product_id = fields.Many2one(
        'product.product',
        string='Interest Product',
        domain=[('type', '=', 'service')]
    )

    interest_analytic_account_id = fields.Many2one(
        'account.analytic.account',
        string='Interest Analytic Account',
        help="Used as the 100% analytic distribution on the interest line when "
             "your company enforces a mandatory analytic distribution. Leave "
             "empty to inherit from the original invoice or auto-detect."
    )

    @api.model
    def get_values(self):
        res = super().get_values()
        params = self.env['ir.config_parameter'].sudo()

        rule_id = int(params.get_param('inom_interest.interest_rule_id', default=0))
        account_id = int(params.get_param('inom_interest.interest_account_id', default=0))
        journal_id = int(params.get_param('inom_interest.interest_journal_id', default=0))
        product_id = int(params.get_param('inom_interest.interest_product_id', default=0))
        analytic_id = int(params.get_param('inom_interest.interest_analytic_account_id', default=0))

        res.update(
            interest_rule_id=rule_id if rule_id else False,
            interest_account_id=account_id if account_id else False,
            interest_journal_id=journal_id if journal_id else False,
            interest_product_id=product_id if product_id else False,
            interest_analytic_account_id=analytic_id if analytic_id else False,
        )
        return res

    def set_values(self):
        super().set_values()
        params = self.env['ir.config_parameter'].sudo()

        params.set_param('inom_interest.interest_rule_id', self.interest_rule_id.id or 0)
        params.set_param('inom_interest.interest_account_id', self.interest_account_id.id or 0)
        params.set_param('inom_interest.interest_journal_id', self.interest_journal_id.id or 0)
        params.set_param('inom_interest.interest_product_id', self.interest_product_id.id or 0)
        params.set_param('inom_interest.interest_analytic_account_id', self.interest_analytic_account_id.id or 0)