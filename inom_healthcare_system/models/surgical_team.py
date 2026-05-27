from odoo import models, fields


class SurgicalTeam(models.Model):
    _name='oehealth.surgical.team'
    _description='Surgical Team'
    _rec_name='member_name'

    surgery_id=fields.Many2one(
        'oehealth.surgery',
        required=True
    )

    member_name=fields.Char(required=True)

    role=fields.Selection([
        ('surgeon','Surgeon'),
        ('assistant','Assistant'),
        ('nurse','Nurse'),
        ('anesthetist','Anesthetist')
    ], required=True)

    supplies=fields.Text(
        string="Supplies Used"
    )