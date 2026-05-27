from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class OEBed(models.Model):
    _name = 'oeh.bed'
    _description = 'Hospital Bed'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'

    # ---- Existing fields (preserved) ----
    name = fields.Char(required=True, tracking=True)
    ward_id = fields.Many2one('oeh.ward', required=True, tracking=True)

    # NOTE: original keys (free/occupied/maintenance) kept for compatibility;
    # new professional states appended.
    status = fields.Selection([
        ('free', 'Free'),
        ('reserved', 'Reserved'),
        ('occupied', 'Occupied'),
        ('cleaning', 'Cleaning'),
        ('maintenance', 'Maintenance'),
    ], default='free', tracking=True)

    # ---- Professional additions ----
    code = fields.Char(string='Bed Ref', default='New', readonly=True, copy=False, index=True)
    bed_type = fields.Selection([
        ('standard', 'Standard'),
        ('electric', 'Electric'),
        ('icu', 'ICU'),
        ('pediatric', 'Pediatric'),
    ], default='standard')
    current_patient_id = fields.Many2one('oeh.patient', string='Current Patient', readonly=True)
    active = fields.Boolean(default=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('code', 'New') in (False, 'New'):
                vals['code'] = self.env['ir.sequence'].next_by_code('oeh.bed') or 'New'
        return super().create(vals_list)

    # ---- Bed allocation workflow ----
    def action_reserve(self):
        for rec in self:
            if rec.status == 'occupied':
                raise ValidationError(_("Bed %s is occupied and cannot be reserved.") % rec.name)
            rec.status = 'reserved'

    def action_occupy(self):
        self.write({'status': 'occupied'})

    def action_free(self):
        self.write({'status': 'free', 'current_patient_id': False})

    def action_cleaning(self):
        self.write({'status': 'cleaning'})

    def action_maintenance(self):
        self.write({'status': 'maintenance'})
