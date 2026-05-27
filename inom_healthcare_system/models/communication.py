from odoo import models, fields

class OeHealthCommunication(models.Model):
    _name = 'oeh.communication'
    _description = 'Communication Module'
    _rec_name = 'patient_id'

    patient_id = fields.Many2one(
        'oeh.patient',
        string="Patient",
        required=True
    )

    doctor_id = fields.Many2one('oeh.doctor', string="Doctor")

    communication_type = fields.Selection([
        ('telemedicine', 'Telemedicine'),
        ('whatsapp', 'WhatsApp'),
        ('sms', 'SMS')
    ], required=True)

    message = fields.Text(string="Message")

    scheduled_time = fields.Datetime()

    status = fields.Selection([
        ('draft', 'Draft'),
        ('sent', 'Sent'),
        ('failed', 'Failed')
    ], default='draft')