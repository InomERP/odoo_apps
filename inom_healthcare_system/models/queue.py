from odoo import models, fields


class QueueToken(models.Model):

    _name = 'inom.queue'
    _description = 'Queue Token'
    _rec_name='token_no'

    token_no = fields.Integer(required=True)

    patient_id = fields.Many2one(
        'inom.patient',
        string='Patient',
        required=True
    )

    doctor_id = fields.Many2one(
        'inom.doctor',
        string='Doctor',
        required=True
    )

    state = fields.Selection([
        ('waiting', 'Waiting'),
        ('in_progress', 'In Progress'),
        ('done', 'Done')
    ], default='waiting')