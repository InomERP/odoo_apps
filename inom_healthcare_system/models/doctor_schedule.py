from odoo import models, fields

class DoctorSchedule(models.Model):

    _name='doctor.schedule'
    _rec_name='doctor_id'

    doctor_id=fields.Many2one(
        'oeh.doctor',
        required=True
    )

    day=fields.Selection([
        ('mon','Monday'),
        ('tue','Tuesday'),
        ('wed','Wednesday'),
        ('thu','Thursday'),
        ('fri','Friday'),
        ('sat','Saturday'),
        ('sun','Sunday')
    ], required=True)

    start_time=fields.Float(required=True)

    end_time=fields.Float(required=True)