from odoo import models,fields


class Vaccination(models.Model):


    _name='patient.vaccination'
    _rec_name='vaccine_name'


    patient_id=fields.Many2one(
        'oeh.patient',
        required=True
    )


    vaccine_name=fields.Char(required=True)

    vaccination_date=fields.Date()

    next_due_date=fields.Date()

    status=fields.Selection([

        ('done','Done'),
        ('pending','Pending')

    ], required=True)