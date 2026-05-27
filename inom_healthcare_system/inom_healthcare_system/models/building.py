from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class OEBuilding(models.Model):
    _name = 'oeh.building'
    _description = 'Hospital Building'
    _rec_name = 'name'

    # ---- Existing fields (preserved) ----
    name = fields.Char(required=True)
    code = fields.Char()
    ward_ids = fields.One2many('oeh.ward', 'building_id')

    # ---- Professional additions ----
    campus_id = fields.Many2one('oeh.campus', string='Campus')
    company_id = fields.Many2one(
        'res.company', string='Company', default=lambda self: self.env.company)
    floors = fields.Integer(string='No. of Floors')
    capacity = fields.Integer(string='Bed Capacity')
    active = fields.Boolean(default=True)
    ward_count = fields.Integer(compute='_compute_building_stats')
    bed_count = fields.Integer(compute='_compute_building_stats')

    def _compute_building_stats(self):
        for rec in self:
            rec.ward_count = len(rec.ward_ids)
            rec.bed_count = len(rec.ward_ids.mapped('bed_ids'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('code', False) in (False, '', 'New'):
                vals['code'] = self.env['ir.sequence'].next_by_code('oeh.building') or vals.get('code')
        return super().create(vals_list)

    @api.constrains('floors', 'capacity')
    def _check_building_numbers(self):
        for rec in self:
            if rec.floors < 0:
                raise ValidationError(_("Number of floors cannot be negative."))
            if rec.capacity < 0:
                raise ValidationError(_("Bed capacity cannot be negative."))

    def action_view_wards(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Wards'),
            'res_model': 'oeh.ward',
            'view_mode': 'list,form',
            'domain': [('building_id', '=', self.id)],
            'context': {'default_building_id': self.id},
        }
