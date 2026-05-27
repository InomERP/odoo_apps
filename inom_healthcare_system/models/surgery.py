from odoo import models, fields, api


class Surgery(models.Model):
    _name = 'oehealth.surgery'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Surgery Management'
    _rec_name = 'name'

    name = fields.Char(
        string="Surgery Ref",
        default='New',
        readonly=True,
        copy=False
    )

    patient_id = fields.Many2one(
        'oeh.patient',
        string="Patient",
        required=True
    )

    doctor_id = fields.Many2one(
        'oeh.doctor',
        string="Surgeon",
        required=True
    )

    surgery_name = fields.Char(
        string="Surgery Name",
        required=True
    )

    surgery_date = fields.Datetime()

    status = fields.Selection([
        ('draft', 'Draft'),
        ('scheduled', 'Scheduled'),
        ('progress', 'In Progress'),
        ('done', 'Done'),
        ('cancel', 'Cancelled')
    ], default='draft', tracking=True)

    asa_score = fields.Selection([
        ('1', 'ASA I'),
        ('2', 'ASA II'),
        ('3', 'ASA III'),
        ('4', 'ASA IV'),
        ('5', 'ASA V')
    ])

    mallampati = fields.Selection([
        ('1', 'Class I'),
        ('2', 'Class II'),
        ('3', 'Class III'),
        ('4', 'Class IV')
    ])

    rcri_score = fields.Integer()

    team_ids = fields.One2many(
        'oehealth.surgical.team',
        'surgery_id'
    )

    ot_ids = fields.One2many(
        'oehealth.ot.schedule',
        'surgery_id'
    )

    anesthesia_ids = fields.One2many(
        'oehealth.anesthesia.record',
        'surgery_id'
    )

    @api.model_create_multi
    def create(self, vals_list):

        for vals in vals_list:

            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env[
                    'ir.sequence'
                ].next_by_code(
                    'oehealth.surgery'
                ) or 'New'

        return super().create(vals_list)

    # =========================
    # STATUS BUTTONS
    # =========================

    def action_schedule(self):
        self.status = 'scheduled'

    def action_progress(self):
        self.status = 'progress'

    def action_done(self):
        self.status = 'done'

    def action_cancel(self):
        self.status = 'cancel'

    def action_reset_draft(self):
        self.status = 'draft'