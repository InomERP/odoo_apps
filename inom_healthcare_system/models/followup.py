from odoo import models, fields

class Followup(models.Model):

    _name='oeh.followup'
    _rec_name='patient_id'

    patient_id=fields.Many2one(
        'oeh.patient',
        required=True
    )

    appointment_id=fields.Many2one(
        'oeh.appointment',
        required=True
    )

    next_date=fields.Date(required=True)

    notes=fields.Text()