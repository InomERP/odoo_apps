from odoo import models,fields


class PatientVisit(models.Model):


    _name='patient.visit'
    _rec_name='patient_id'

    _order='visit_date desc'


    patient_id=fields.Many2one(
        'oeh.patient',
        required=True
    )


    visit_date=fields.Datetime(required=True)

    doctor=fields.Char(required=True)

    chief_complaint=fields.Text()

    diagnosis=fields.Text()

    notes=fields.Text()