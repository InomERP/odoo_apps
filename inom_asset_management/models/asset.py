from odoo import models, fields
from datetime import timedelta

class Asset(models.Model):
    _name = 'asset.asset.custom'
    _description = 'Asset'

    name = fields.Char(required=True)
    reference = fields.Char()

    category_id = fields.Many2one('asset.category.custom')
    purchase_date = fields.Date("Purchase Date")
    gross_value = fields.Float("Gross Value")
    salvage_value = fields.Float("Salvage Value")

    date = fields.Date("Purchase Date")
    first_depreciation_date = fields.Date()

    value = fields.Float("Gross Value")
    salvage_value = fields.Float()

    state = fields.Selection([
        ('draft', 'Draft'),
        ('running', 'Running'),
        ('close', 'Closed')
    ], default='draft')

    depreciation_line_ids = fields.One2many(
        'asset.depreciation.line',
        'asset_id',
        string="Depreciation Lines"
    )

    def action_compute(self):
        for rec in self:
            rec.depreciation_line_ids.unlink()

            number = rec.category_id.method_number or 5
            period = rec.category_id.method_period or 1

            amount = (rec.value - rec.salvage_value) / number
            total = 0

            date = rec.first_depreciation_date or fields.Date.today()

            for i in range(number):
                total += amount

                self.env['asset.depreciation.line'].create({
                    'asset_id': rec.id,
                    'depreciation_date': date,
                    'amount': amount,
                    'cumulative_value': total,
                    'remaining_value': rec.value - total,
                })

                date = date + timedelta(days=30 * period)

            rec.state = 'running'