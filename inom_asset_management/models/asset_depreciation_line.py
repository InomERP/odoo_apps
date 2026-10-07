from odoo import models, fields

class AssetDepreciationLine(models.Model):
    _name = 'asset.depreciation.line'
    _description = 'Depreciation Line'

    asset_id = fields.Many2one(
        'asset.asset.custom',
        string="Asset"
    )

    depreciation_date = fields.Date()
    amount = fields.Float()
    cumulative_value = fields.Float()
    remaining_value = fields.Float()