# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class InomCostTakeoffLine(models.Model):
    """A single measurement behind a material quantity.

    This is what estimators keep in a spreadsheet: rooms, walls, openings,
    each with its own dimensions, adding up to the quantity that gets priced.
    Keeping it in the estimate means the number can be checked and revised
    later instead of being a figure nobody can explain six months on.
    """
    _name = 'inom.cost.takeoff.line'
    _description = 'Job Cost Measurement / Takeoff Line'
    _order = 'sequence, id'

    sequence = fields.Integer(default=10)
    material_line_id = fields.Many2one(
        'inom.cost.material.line', string='Material Line',
        required=True, ondelete='cascade', index=True)
    name = fields.Char(string='Location / Description', required=True)
    measure_type = fields.Selection([
        ('count', 'Count'),
        ('length', 'Length'),
        ('area', 'Area'),
        ('volume', 'Volume'),
    ], string='Measure', required=True, default='area')
    count = fields.Float(string='Nos.', default=1.0)
    length = fields.Float(string='Length')
    width = fields.Float(string='Width')
    height = fields.Float(string='Height')
    is_deduction = fields.Boolean(
        string='Deduct',
        help='Subtract instead of add - doors, windows and other openings.')
    quantity = fields.Float(string='Quantity', compute='_compute_quantity',
                            store=True)
    quantity_signed = fields.Float(string='Net', compute='_compute_quantity',
                                   store=True)

    @api.depends('measure_type', 'count', 'length', 'width', 'height',
                 'is_deduction')
    def _compute_quantity(self):
        for line in self:
            nos = line.count or 0.0
            if line.measure_type == 'count':
                qty = nos
            elif line.measure_type == 'length':
                qty = nos * (line.length or 0.0)
            elif line.measure_type == 'area':
                qty = nos * (line.length or 0.0) * (line.width or 0.0)
            else:
                qty = (nos * (line.length or 0.0) * (line.width or 0.0)
                       * (line.height or 0.0))
            line.quantity = qty
            line.quantity_signed = -qty if line.is_deduction else qty

    def _check_estimate_open(self):
        if self.env.context.get('inom_allow_locked_write'):
            return
        for line in self:
            estimate = line.material_line_id.estimate_id
            if estimate.state in ('approved', 'converted'):
                raise UserError(_(
                    'Estimate %(ref)s is %(state)s and its measurements can no '
                    'longer be changed.',
                    ref=estimate.name, state=estimate.state))

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        lines._check_estimate_open()
        return lines

    def write(self, vals):
        self._check_estimate_open()
        return super().write(vals)

    def unlink(self):
        self._check_estimate_open()
        return super().unlink()
