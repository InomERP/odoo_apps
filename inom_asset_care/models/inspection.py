# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class InomInspectionTemplate(models.Model):
    _name = 'inom.inspection.template'
    _description = 'Inspection Template'

    name = fields.Char(string='Template Name', required=True)
    category_id = fields.Many2one(
        'inom.asset.category', string='Applicable Category')
    line_ids = fields.One2many(
        'inom.inspection.template.line', 'template_id',
        string='Checkpoints')
    company_id = fields.Many2one(
        'res.company', string='Company',
        default=lambda self: self.env.company)
    active = fields.Boolean(default=True)


class InomInspectionTemplateLine(models.Model):
    _name = 'inom.inspection.template.line'
    _description = 'Inspection Template Checkpoint'
    _order = 'sequence, id'

    template_id = fields.Many2one(
        'inom.inspection.template', string='Template', required=True,
        ondelete='cascade')
    sequence = fields.Integer(default=10)
    name = fields.Char(string='Checkpoint', required=True)
    answer_type = fields.Selection([
        ('pass_fail', 'Pass / Fail'),
        ('numeric', 'Numeric Reading'),
        ('text', 'Observation Text'),
    ], string='Answer Type', default='pass_fail', required=True)
    min_value = fields.Float(string='Minimum Acceptable')
    max_value = fields.Float(string='Maximum Acceptable')


class InomAssetInspection(models.Model):
    _name = 'inom.asset.inspection'
    _description = 'Asset Inspection'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'inspection_date desc, id desc'

    name = fields.Char(
        string='Inspection Reference', required=True, copy=False,
        readonly=True, default=lambda self: _('New'))
    asset_id = fields.Many2one(
        'inom.asset', string='Asset', required=True, tracking=True)
    template_id = fields.Many2one(
        'inom.inspection.template', string='Template')
    inspector_id = fields.Many2one(
        'res.users', string='Inspector',
        default=lambda self: self.env.user)
    inspection_date = fields.Date(
        string='Inspection Date', default=fields.Date.context_today)
    line_ids = fields.One2many(
        'inom.asset.inspection.line', 'inspection_id',
        string='Checkpoint Results')
    overall_result = fields.Selection([
        ('pass', 'Passed'),
        ('fail', 'Failed'),
    ], string='Overall Result', compute='_compute_overall_result',
        store=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
    ], string='Status', default='draft', tracking=True)
    remarks = fields.Text(string='Inspector Remarks')
    followup_request_id = fields.Many2one(
        'inom.maintenance.request', string='Follow-up Request',
        readonly=True, copy=False)
    company_id = fields.Many2one(
        'res.company', string='Company', required=True,
        default=lambda self: self.env.company)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'inom.asset.inspection') or _('New')
        return super().create(vals_list)

    @api.depends('line_ids.result')
    def _compute_overall_result(self):
        for inspection in self:
            if inspection.line_ids and any(
                    line.result == 'fail' for line in inspection.line_ids):
                inspection.overall_result = 'fail'
            else:
                inspection.overall_result = 'pass'

    @api.onchange('template_id')
    def _onchange_template_id(self):
        if self.template_id:
            self.line_ids = [(5, 0, 0)] + [(0, 0, {
                'name': tline.name,
                'answer_type': tline.answer_type,
                'min_value': tline.min_value,
                'max_value': tline.max_value,
                'sequence': tline.sequence,
            }) for tline in self.template_id.line_ids]

    def action_start(self):
        self.write({'state': 'in_progress'})

    def action_complete(self):
        for inspection in self:
            if not inspection.line_ids:
                raise UserError(_(
                    'Add at least one checkpoint result before completing '
                    'the inspection.'))
            inspection.state = 'completed'
            if inspection.overall_result == 'fail' \
                    and not inspection.followup_request_id:
                request = self.env['inom.maintenance.request'].create({
                    'title': _('Follow-up: failed inspection %s',
                               inspection.name),
                    'asset_id': inspection.asset_id.id,
                    'request_type': 'inspection',
                    'priority': '2',
                    'description': inspection.remarks or '',
                })
                inspection.followup_request_id = request
                inspection.message_post(body=_(
                    'Maintenance request %s created automatically for the '
                    'failed checkpoints.', request.name))


class InomAssetInspectionLine(models.Model):
    _name = 'inom.asset.inspection.line'
    _description = 'Asset Inspection Checkpoint Result'
    _order = 'sequence, id'

    inspection_id = fields.Many2one(
        'inom.asset.inspection', string='Inspection', required=True,
        ondelete='cascade')
    sequence = fields.Integer(default=10)
    name = fields.Char(string='Checkpoint', required=True)
    answer_type = fields.Selection([
        ('pass_fail', 'Pass / Fail'),
        ('numeric', 'Numeric Reading'),
        ('text', 'Observation Text'),
    ], string='Answer Type', default='pass_fail', required=True)
    numeric_value = fields.Float(string='Reading')
    min_value = fields.Float(string='Minimum Acceptable')
    max_value = fields.Float(string='Maximum Acceptable')
    observation = fields.Char(string='Observation')
    result = fields.Selection([
        ('pass', 'Pass'),
        ('fail', 'Fail'),
    ], string='Result', compute='_compute_result', store=True,
        readonly=False)

    @api.depends('answer_type', 'numeric_value', 'min_value', 'max_value')
    def _compute_result(self):
        for line in self:
            if line.answer_type == 'numeric' and (
                    line.min_value or line.max_value):
                in_range = True
                if line.min_value and line.numeric_value < line.min_value:
                    in_range = False
                if line.max_value and line.numeric_value > line.max_value:
                    in_range = False
                line.result = 'pass' if in_range else 'fail'
            elif not line.result:
                line.result = 'pass'
