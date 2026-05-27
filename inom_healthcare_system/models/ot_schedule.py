from odoo import models, fields

class OTSchedule(models.Model):
    _name='oehealth.ot.schedule'
    _description='OT Scheduling'
    _rec_name='surgery_id'

    surgery_id=fields.Many2one(
        'oehealth.surgery',
        required=True
    )

    ot_room=fields.Char(required=True)

    start_time=fields.Datetime(required=True)

    end_time=fields.Datetime(required=True)

    notes=fields.Text()