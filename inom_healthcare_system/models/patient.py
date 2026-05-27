from odoo import models, fields, api


class OEPatient(models.Model):

    _name = 'oeh.patient'
    _description = 'Patient'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'

    patient_id = fields.Char(
        string='Patient ID',
        readonly=True,
        default='New',
        copy=False
    )

    name = fields.Char(
        string='Patient Name',
        required=True,
        tracking=True
    )

    image_1920 = fields.Image()

    dob = fields.Date()

    age = fields.Integer()

    gender = fields.Selection([
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other')
    ])

    blood_group = fields.Selection([
        ('a+', 'A+'),
        ('a-', 'A-'),
        ('b+', 'B+'),
        ('b-', 'B-'),
        ('o+', 'O+'),
        ('o-', 'O-'),
        ('ab+', 'AB+'),
        ('ab-', 'AB-')
    ])

    phone = fields.Char()

    email = fields.Char()

    address = fields.Text()

    emergency_contact = fields.Char()

    family_member_ids = fields.Many2many(
        'oeh.patient',
        'oeh_patient_family_rel',
        'patient_id',
        'family_id',
        string="Family Members"
    )

    allergy_ids = fields.One2many(
        'patient.allergy',
        'patient_id'
    )

    history_ids = fields.One2many(
        'patient.history',
        'patient_id'
    )

    vaccination_ids = fields.One2many(
        'patient.vaccination',
        'patient_id'
    )

    visit_ids = fields.One2many(
        'patient.visit',
        'patient_id'
    )

    active = fields.Boolean(
        default=True
    )

    # -------------------------
    # Community ERP Features
    # -------------------------

    partner_id = fields.Many2one(
        'res.partner',
        string='Contact'
    )

    crm_lead_id = fields.Many2one(
        'crm.lead',
        string='CRM Lead'
    )

    appointment_count = fields.Integer(
        compute='_compute_appointment_count'
    )

    visit_count = fields.Integer(
        compute='_compute_visit_count'
    )

    @api.depends()
    def _compute_appointment_count(self):

        for rec in self:

            rec.appointment_count = self.env[
                'oeh.appointment'
            ].search_count([
                ('patient_id', '=', rec.id)
            ])


    @api.depends()
    def _compute_visit_count(self):

        for rec in self:

            rec.visit_count = self.env[
                'patient.visit'
            ].search_count([
                ('patient_id', '=', rec.id)
            ])


    def action_view_appointments(self):

        self.ensure_one()

        return {
            'type': 'ir.actions.act_window',
            'name': 'Appointments',
            'res_model': 'oeh.appointment',
            'view_mode': 'list,form',
            'domain': [
                ('patient_id', '=', self.id)
            ]
        }


    def action_view_visits(self):

        self.ensure_one()

        return {
            'type': 'ir.actions.act_window',
            'name': 'Visits',
            'res_model': 'patient.visit',
            'view_mode': 'list,form',
            'domain': [
                ('patient_id', '=', self.id)
            ]
        }


    @api.model_create_multi
    def create(self, vals_list):

        for vals in vals_list:

            if vals.get(
                'patient_id',
                'New'
            ) == 'New':

                vals['patient_id'] = self.env[
                    'ir.sequence'
                ].next_by_code(
                    'oeh.patient'
                ) or 'New'

        return super().create(vals_list)


    def name_get(self):

        result = []

        for rec in self:

            display_name = "%s [%s]" % (
                rec.name or '',
                rec.patient_id or ''
            )

            result.append(
                (rec.id, display_name)
            )

        return result








# from odoo import models, fields, api


# class OEPatient(models.Model):

#     _name = 'oeh.patient'
#     _description = 'Patient'
#     _inherit = ['mail.thread', 'mail.activity.mixin']

#     # Display patient name in relations
#     _rec_name = 'name'


#     patient_id = fields.Char(
#         string='Patient ID',
#         readonly=True,
#         default='New',
#         copy=False
#     )

#     name = fields.Char(
#         string='Patient Name',
#         required=True,
#         tracking=True
#     )

#     image_1920 = fields.Image()

#     dob = fields.Date()

#     age = fields.Integer()

#     gender = fields.Selection([
#         ('male', 'Male'),
#         ('female', 'Female'),
#         ('other', 'Other')
#     ])

#     blood_group = fields.Selection([
#         ('a+', 'A+'),
#         ('a-', 'A-'),
#         ('b+', 'B+'),
#         ('b-', 'B-'),
#         ('o+', 'O+'),
#         ('o-', 'O-'),
#         ('ab+', 'AB+'),
#         ('ab-', 'AB-')
#     ])

#     phone = fields.Char()

#     email = fields.Char()

#     address = fields.Text()

#     emergency_contact = fields.Char()


#     # Self relation fixed
#     family_member_ids = fields.Many2many(
#         'oeh.patient',
#         'oeh_patient_family_rel',
#         'patient_id',
#         'family_id',
#         string="Family Members"
#     )


#     allergy_ids = fields.One2many(
#         'patient.allergy',
#         'patient_id'
#     )

#     history_ids = fields.One2many(
#         'patient.history',
#         'patient_id'
#     )

#     vaccination_ids = fields.One2many(
#         'patient.vaccination',
#         'patient_id'
#     )

#     visit_ids = fields.One2many(
#         'patient.visit',
#         'patient_id'
#     )


#     active = fields.Boolean(
#         default=True
#     )


#     @api.model_create_multi
#     def create(self, vals_list):

#         for vals in vals_list:

#             if vals.get(
#                 'patient_id',
#                 'New'
#             ) == 'New':

#                 vals['patient_id'] = self.env[
#                     'ir.sequence'
#                 ].next_by_code(
#                     'oeh.patient'
#                 ) or 'New'

#         return super().create(vals_list)


#     def name_get(self):

#         result = []

#         for rec in self:

#             display_name = "%s [%s]" % (
#                 rec.name or '',
#                 rec.patient_id or ''
#             )

#             result.append(
#                 (rec.id, display_name)
#             )

#         return result