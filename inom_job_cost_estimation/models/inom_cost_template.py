# -*- coding: utf-8 -*-
from odoo import api, fields, models


class InomCostTemplate(models.Model):
    _name = 'inom.cost.template'
    _description = 'Job Cost Estimate Template'
    _order = 'name'

    name = fields.Char(string='Template Name', required=True)
    category_id = fields.Many2one('inom.cost.category', string='Job Category')
    active = fields.Boolean(string='Active', default=True)
    note = fields.Text(string='Notes')
    line_ids = fields.One2many('inom.cost.template.line', 'template_id',
                               string='Template Lines', copy=True)


class InomCostTemplateLine(models.Model):
    _name = 'inom.cost.template.line'
    _description = 'Job Cost Template Line'
    _order = 'line_type, sequence, id'

    sequence = fields.Integer(default=10)
    template_id = fields.Many2one('inom.cost.template', string='Template',
                                  required=True, ondelete='cascade')
    line_type = fields.Selection([
        ('material', 'Material'),
        ('labour', 'Manpower'),
        ('equipment', 'Equipment'),
        ('overhead', 'Indirect Cost'),
    ], string='Type', required=True, default='material')
    product_id = fields.Many2one('product.product', string='Product')
    job_id = fields.Many2one('hr.job', string='Job Position')
    name = fields.Char(string='Description', required=True)
    quantity = fields.Float(string='Quantity', default=1.0)
    uom_id = fields.Many2one('uom.uom', string='UoM')
    hours = fields.Float(string='Hours', default=1.0)
    price_unit = fields.Float(string='Unit Cost / Rate')
    amount = fields.Float(string='Amount')

    @api.onchange('product_id')
    def _onchange_product_id(self):
        for line in self:
            if not line.product_id:
                continue
            if not line.name:
                line.name = line.product_id.display_name
            if not line.price_unit:
                line.price_unit = line.product_id.standard_price
            # Only material is measured in a unit of measure; manpower is
            # priced per hour and equipment per period.
            if line.line_type == 'material':
                line.uom_id = line.product_id.uom_id
