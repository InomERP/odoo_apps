from odoo import models, fields


class ClinicalEvaluation(models.Model):
    _name='oeh.clinical'
    _description='Clinical Evaluation'
    _rec_name='patient_id'

    patient_id=fields.Many2one(
        'oeh.patient',
        required=True
    )

    appointment_id=fields.Many2one(
        'oeh.appointment'
    )

    doctor_id=fields.Many2one(
        'oeh.doctor'
    )

    symptoms=fields.Text()

    diagnosis=fields.Text()

    notes=fields.Html()