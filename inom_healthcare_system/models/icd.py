from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ICD(models.Model):

    _name = 'oeh.icd'
    _description = 'ICD Codes'
    _inherit = ['mail.thread']
    _rec_name = 'code'
    _order = 'code'

    # ---- Existing fields (preserved) ----
    code = fields.Char(required=True, index=True, tracking=True)
    name = fields.Char(required=True, tracking=True)
    type = fields.Selection([
        ('icd10', 'ICD-10'),
        ('icd11', 'ICD-11'),
    ], required=True, tracking=True)

    # ---- Professional additions ----
    active = fields.Boolean(default=True)
    category = fields.Char(string='Category / Chapter', index=True)
    description = fields.Text()
    treatment_count = fields.Integer(compute='_compute_usage')

    _sql_constraints = [
        ('icd_code_type_uniq', 'unique(code, type)',
         'This ICD code already exists for the selected classification.'),
    ]

    def _compute_usage(self):
        Treatment = self.env['oeh.treatment']
        for rec in self:
            rec.treatment_count = Treatment.search_count([('diagnosis_id', '=', rec.id)])

    @api.depends('code', 'name')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = ('%s - %s' % (rec.code, rec.name)) if rec.code else (rec.name or '')

    @api.constrains('code')
    def _check_code(self):
        for rec in self:
            if not rec.code or not rec.code.strip():
                raise ValidationError(_("ICD code cannot be empty."))

    def action_view_treatments(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window', 'name': _('Treatments'),
            'res_model': 'oeh.treatment', 'view_mode': 'list,form',
            'domain': [('diagnosis_id', '=', self.id)],
        }
