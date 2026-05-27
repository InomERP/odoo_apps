from odoo import models,fields


class MedicalHistory(models.Model):

    _name='patient.history'
    _rec_name='disease'


    patient_id=fields.Many2one(
        'oeh.patient',
        required=True
    )

    disease=fields.Char(required=True)

    diagnosed_date=fields.Date()

    notes=fields.Text()