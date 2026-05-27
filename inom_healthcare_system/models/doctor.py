from odoo import models, fields


class HMSDoctor(models.Model):
    _name='oeh.doctor'
    _description='Doctor'
    _rec_name='name'
    _inherit=['mail.thread','mail.activity.mixin']

    name=fields.Char(
        required=True,
        tracking=True
    )

    specialization=fields.Char()

    phone=fields.Char()

    email=fields.Char()

    schedule_ids=fields.One2many(
        'doctor.schedule',
        'doctor_id'
    )

    employee_id=fields.Many2one(
        'hr.employee',
        string='Employee'
    )

    attendance_count=fields.Integer(
        compute='_compute_attendance'
    )

    leave_count=fields.Integer(
        compute='_compute_leave'
    )


    def _compute_attendance(self):

        for rec in self:

            rec.attendance_count=self.env[
                'hr.attendance'
            ].search_count([
                ('employee_id','=',rec.employee_id.id)
            ])


    def _compute_leave(self):

        for rec in self:

            rec.leave_count=self.env[
                'hr.leave'
            ].search_count([
                ('employee_id','=',rec.employee_id.id)
            ])


    def action_view_attendance(self):

        self.ensure_one()

        action=self.env.ref(
            'hr_attendance.hr_attendance_action'
        ).read()[0]

        action['domain']=[
            ('employee_id','=',self.employee_id.id)
        ]

        return action


    def action_view_leave(self):

        self.ensure_one()

        action=self.env.ref(
            'hr_holidays.hr_leave_action_action_approve_department'
        ).read()[0]

        action['domain']=[
            ('employee_id','=',self.employee_id.id)
        ]

        return action







# from odoo import models, fields


# class HMSDoctor(models.Model):
#     _name='oeh.doctor'
#     _description='Doctor'
#     _rec_name='name'

#     name=fields.Char(required=True)

#     specialization=fields.Char()

#     phone=fields.Char()

#     email=fields.Char()

#     schedule_ids=fields.One2many(
#         'doctor.schedule',
#         'doctor_id'
#     )