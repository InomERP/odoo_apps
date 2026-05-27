from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class OEWard(models.Model):
    _name = 'oeh.ward'
    _description = 'Hospital Ward'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'

    # ---- Existing fields (preserved) ----
    name = fields.Char(required=True, tracking=True)
    building_id = fields.Many2one('oeh.building', required=True, tracking=True)
    bed_ids = fields.One2many('oeh.bed', 'ward_id')

    # ---- Professional additions ----
    code = fields.Char(string='Ward Code', default='New', readonly=True, copy=False, index=True)
    ward_type = fields.Selection([
        ('general', 'General'),
        ('semi_private', 'Semi-Private'),
        ('private', 'Private'),
        ('icu', 'ICU'),
        ('isolation', 'Isolation'),
        ('maternity', 'Maternity'),
        ('pediatric', 'Pediatric'),
    ], default='general', tracking=True)
    is_isolation = fields.Boolean(string='Isolation Ward', tracking=True)
    nurse_in_charge = fields.Char(string='Nurse In-Charge')
    state = fields.Selection([
        ('active', 'Active'),
        ('maintenance', 'Under Maintenance'),
        ('closed', 'Closed'),
    ], default='active', tracking=True)

    bed_count = fields.Integer(compute='_compute_ward_stats')
    occupied_count = fields.Integer(compute='_compute_ward_stats')
    available_count = fields.Integer(compute='_compute_ward_stats')
    occupancy_rate = fields.Float(string='Occupancy %', compute='_compute_ward_stats')

    @api.depends('bed_ids', 'bed_ids.status')
    def _compute_ward_stats(self):
        for rec in self:
            beds = rec.bed_ids
            rec.bed_count = len(beds)
            rec.occupied_count = len(beds.filtered(lambda b: b.status == 'occupied'))
            rec.available_count = len(beds.filtered(lambda b: b.status == 'free'))
            rec.occupancy_rate = (rec.occupied_count / rec.bed_count * 100.0) if rec.bed_count else 0.0

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('code', 'New') in (False, 'New'):
                vals['code'] = self.env['ir.sequence'].next_by_code('oeh.ward') or 'New'
        return super().create(vals_list)

    # ---- Workflow ----
    def action_set_active(self):
        self.write({'state': 'active'})

    def action_set_maintenance(self):
        self.write({'state': 'maintenance'})

    def action_close(self):
        self.write({'state': 'closed'})

    def action_view_beds(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Beds'),
            'res_model': 'oeh.bed',
            'view_mode': 'list,form',
            'domain': [('ward_id', '=', self.id)],
            'context': {'default_ward_id': self.id},
        }
