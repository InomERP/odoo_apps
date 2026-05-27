from odoo import models, fields


class OESample(models.Model):

    _name = 'oeh.sample'
    _description = 'Sample Tracking'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'barcode'

    patient_id = fields.Many2one(
        'oeh.patient',
        required=True,
        tracking=True
    )

    barcode = fields.Char(
        required=True,
        tracking=True
    )

    sample_type = fields.Char(
        tracking=True
    )

    collected_date = fields.Datetime(
        default=fields.Datetime.now
    )

    status = fields.Selection([
        ('collected', 'Collected'),
        ('processing', 'Processing'),
        ('done', 'Done')
    ], default='collected', tracking=True)