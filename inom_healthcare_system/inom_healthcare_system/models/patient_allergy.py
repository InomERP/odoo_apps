from odoo import models,fields


class Allergy(models.Model):

    _name='patient.allergy'
    _rec_name='allergy_name'


    patient_id=fields.Many2one(
        'oeh.patient',
        required=True
    )


    allergy_name=fields.Char(required=True)


    severity=fields.Selection([

        ('low','Low'),
        ('medium','Medium'),
        ('high','High')

    ], required=True)


    notes=fields.Text()