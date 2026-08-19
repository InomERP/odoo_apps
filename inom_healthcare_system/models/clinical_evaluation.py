from odoo import models, fields


class ClinicalEvaluation(models.Model):
    _name='inom.clinical'
    _description='Clinical Evaluation'
    _rec_name='patient_id'

    patient_id=fields.Many2one(
        'inom.patient',
        required=True
    )

    appointment_id=fields.Many2one(
        'inom.appointment'
    )

    doctor_id=fields.Many2one(
        'inom.doctor'
    )

    symptoms=fields.Text()

    diagnosis=fields.Text()

    notes=fields.Html()