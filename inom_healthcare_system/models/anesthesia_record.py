from odoo import models, fields


class AnesthesiaRecord(models.Model):
    _name = 'inom.anesthesia.record'
    _description = 'Anesthesia Record'
    _rec_name = 'anesthetist'   # Record name

    surgery_id = fields.Many2one(
        'inom.surgery',
        required=True
    )

    anesthesia_type = fields.Selection([
        ('general', 'General'),
        ('local', 'Local'),
        ('spinal', 'Spinal'),
        ('epidural', 'Epidural')
    ], required=True)

    anesthetist = fields.Char(
        required=True
    )

    medication = fields.Text()

    notes = fields.Text()