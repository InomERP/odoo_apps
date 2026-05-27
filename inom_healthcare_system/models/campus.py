from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class OECampus(models.Model):
    _name = 'oeh.campus'
    _description = 'Multi Campus'
    _rec_name = 'name'

    # ---- Existing fields (preserved) ----
    name = fields.Char(required=True)
    location = fields.Char()
    phone = fields.Char()

    # ---- Professional additions ----
    code = fields.Char(string='Campus Code', default='New', readonly=True, copy=False, index=True)
    active = fields.Boolean(default=True)
    email = fields.Char()
    company_id = fields.Many2one(
        'res.company', string='Company',
        default=lambda self: self.env.company)
    building_ids = fields.One2many('oeh.building', 'campus_id', string='Buildings')
    building_count = fields.Integer(compute='_compute_building_count')

    def _compute_building_count(self):
        for rec in self:
            rec.building_count = len(rec.building_ids)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('code', 'New') in (False, 'New'):
                vals['code'] = self.env['ir.sequence'].next_by_code('oeh.campus') or 'New'
        return super().create(vals_list)

    def action_view_buildings(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Buildings'),
            'res_model': 'oeh.building',
            'view_mode': 'list,form',
            'domain': [('campus_id', '=', self.id)],
            'context': {'default_campus_id': self.id},
        }
