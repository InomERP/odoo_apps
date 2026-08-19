from odoo import models, fields


class OERadiology(models.Model):

    _name = 'inom.radiology'
    _description = 'Radiology'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'scan_type'

    patient_id = fields.Many2one(
        'inom.patient',
        required=True,
        tracking=True
    )

    scan_type = fields.Char(
        required=True,
        tracking=True
    )

    image = fields.Image()

    report = fields.Html()

    status = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Done')
    ], default='draft', tracking=True)