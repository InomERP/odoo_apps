from odoo import models, fields, api
from datetime import timedelta


class Appointment(models.Model):

    _name = 'oeh.appointment'
    _description = 'Appointment'
    _rec_name = 'appointment_no'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    appointment_no = fields.Char(
        default='New',
        readonly=True,
        tracking=True
    )

    patient_id = fields.Many2one(
        'oeh.patient',
        required=True,
        tracking=True
    )

    doctor_id = fields.Many2one(
        'oeh.doctor',
        required=True,
        tracking=True
    )

    appointment_date = fields.Datetime(
        required=True,
        tracking=True
    )

    chief_complaint = fields.Text()

    followup_date = fields.Date()

    queue_no = fields.Integer()

    meeting_id = fields.Many2one(
        'calendar.event',
        string='Meeting'
    )

    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirmed'),
        ('progress', 'In Progress'),
        ('done', 'Done'),
        ('cancel', 'Cancelled')
    ], default='draft', tracking=True)


    @api.model_create_multi
    def create(self, vals_list):

        for vals in vals_list:

            if vals.get(
                'appointment_no',
                'New'
            ) == 'New':

                vals['appointment_no'] = self.env[
                    'ir.sequence'
                ].next_by_code(
                    'oeh.appointment'
                ) or 'New'

        return super().create(vals_list)


    def action_confirm(self):

        for rec in self:

            rec.state = 'confirm'

            if (
                rec.appointment_date
                and not rec.meeting_id
            ):

                start = rec.appointment_date

                stop = (
                    rec.appointment_date
                    + timedelta(hours=1)
                )

                meeting = self.env[
                    'calendar.event'
                ].create({

                    'name':
                    'Appointment - %s'
                    % rec.patient_id.name,

                    'start': start,

                    'stop': stop,

                })

                rec.meeting_id = meeting.id


    def action_progress(self):

        self.state = 'progress'


    def action_done(self):

        self.state = 'done'


    def action_cancel(self):

        self.state = 'cancel'


    def action_open_meeting(self):

        self.ensure_one()

        if not self.meeting_id:
            return

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'calendar.event',
            'res_id': self.meeting_id.id,
            'view_mode': 'form',
            'target': 'current',
        }







# from odoo import models, fields, api


# class Appointment(models.Model):

#     _name='oeh.appointment'
#     _description='Appointment'
#     _rec_name='appointment_no'


#     appointment_no=fields.Char(
#         default='New',
#         readonly=True
#     )

#     patient_id=fields.Many2one(
#         'oeh.patient',
#         required=True
#     )

#     doctor_id=fields.Many2one(
#         'oeh.doctor',
#         required=True
#     )

#     appointment_date=fields.Datetime()

#     chief_complaint=fields.Text()

#     followup_date=fields.Date()

#     state=fields.Selection([
#         ('draft','Draft'),
#         ('confirm','Confirmed'),
#         ('done','Done'),
#         ('cancel','Cancelled')
#     ],default='draft')

#     queue_no=fields.Integer()

#     @api.model_create_multi
#     def create(self, vals_list):

#         for vals in vals_list:

#             if vals.get(
#                 'appointment_no',
#                 'New'
#             ) == 'New':

#                 vals['appointment_no'] = self.env[
#                     'ir.sequence'
#                 ].next_by_code(
#                     'oeh.appointment'
#                 ) or 'New'

#         return super().create(vals_list)