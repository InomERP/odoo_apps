from odoo import models, fields


class OELaboratory(models.Model):

    _name = 'oeh.laboratory'
    _description = 'Laboratory'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'test_name'

    patient_id = fields.Many2one(
        'oeh.patient',
        string='Patient',
        required=True,
        tracking=True
    )

    test_name = fields.Char(
        required=True,
        tracking=True
    )

    test_date = fields.Date(
        default=fields.Date.context_today
    )

    result = fields.Text()

    status = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Done')
    ], default='draft', tracking=True)