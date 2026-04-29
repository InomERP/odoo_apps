from odoo import models, fields

class AssetCategory(models.Model):
    _name = 'asset.category.custom'
    _description = 'Asset Category'

    name = fields.Char("Asset Name", required=True)

    # Accounts
    journal_id = fields.Many2one('account.journal', string="Journal")
    asset_account_id = fields.Many2one('account.account', string="Asset Account")
    depreciation_account_id = fields.Many2one('account.account', string="Depreciation Account")
    expense_account_id = fields.Many2one('account.account', string="Expense Account")

    # Periodicity
    method_time = fields.Selection([
        ('number', 'Based on Number'),
        ('end', 'Based on Time')
    ], string="Computation", default='number')

    method_number = fields.Integer("Number of Depreciations")
    method_period = fields.Integer("Period Length")
    method_end = fields.Date("Ending Date")

    # Options
    auto_confirm = fields.Boolean("Auto Confirm")
    group_entries = fields.Boolean("Group Entries")

    depreciation_type = fields.Selection([
        ('manual', 'Manual')
    ], string="Depreciation Type", default='manual')

    # Depreciation
    method = fields.Selection([
        ('linear', 'Linear'),
        ('degressive', 'Degressive')
    ], string="Method", default='linear')

    prorata = fields.Boolean("Prorata")