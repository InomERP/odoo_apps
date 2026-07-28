# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class InomCostLineMarkupMixin(models.AbstractModel):
    """Per-line markup override shared by every cost line type.

    A line normally inherits the markup set on the estimate header. Ticking
    ``has_custom_markup`` lets that single line carry its own percentage, which
    is how most contractors actually quote: a low markup on bought-in material
    and a much higher one on their own labour.
    """
    _name = 'inom.cost.line.markup.mixin'
    _description = 'Job Cost Line Markup Mixin'

    has_custom_markup = fields.Boolean(
        string='Custom Markup',
        help='Use a markup specific to this line instead of the one set on the '
             'estimate.')
    markup_percent = fields.Float(string='Markup (%)')
    has_custom_discount = fields.Boolean(
        string='Custom Discount',
        help='Use a discount specific to this line instead of the one set on '
             'the estimate.')
    discount_percent = fields.Float(string='Disc. (%)')

    def _get_effective_markup(self):
        self.ensure_one()
        if self.has_custom_markup:
            return self.markup_percent or 0.0
        return self.estimate_id.markup_percent or 0.0

    def _get_markup_factor(self):
        self.ensure_one()
        return 1.0 + self._get_effective_markup() / 100.0

    def _check_estimate_open(self):
        """Refuse edits to lines of an approved or converted estimate.

        The estimate's own write() guards the one2many path used by the form.
        This covers the other route - editing a line record directly, from an
        import, a server action or the API.
        """
        if self.env.context.get('inom_allow_locked_write'):
            return
        for line in self:
            estimate = line.estimate_id
            if estimate.state in ('approved', 'converted'):
                raise UserError(_(
                    'Estimate %(ref)s is %(state)s and its cost lines can no '
                    'longer be changed. Use New Revision instead.',
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

    def _get_effective_discount(self):
        self.ensure_one()
        if self.has_custom_discount:
            return self.discount_percent or 0.0
        return self.estimate_id.discount_percent or 0.0

    def _get_discount_factor(self):
        self.ensure_one()
        return 1.0 - self._get_effective_discount() / 100.0

    @api.depends('price_subtotal', 'has_custom_markup', 'markup_percent',
                 'has_custom_discount', 'discount_percent',
                 'estimate_id.markup_percent', 'estimate_id.discount_percent')
    def _compute_price_sell(self):
        """Gross is cost plus markup; net is gross less discount.

        Both are kept because the customer has to see what the discount was
        taken off, while every roll-up and the margin must use the net figure.
        Discounting therefore eats margin, which is exactly what the estimator
        needs to watch.
        """
        for line in self:
            gross = line.price_subtotal * line._get_markup_factor()
            line.price_gross = gross
            line.price_sell = gross * line._get_discount_factor()

    def _get_sell_quantity(self):
        """Quantity the customer-facing unit price should be divided by.

        Overridden per line type: material sells per unit, manpower per
        man-hour, equipment per unit-period. Indirect costs are a lump sum.
        """
        self.ensure_one()
        return 1.0

    @api.depends('price_gross')
    def _compute_price_unit_sell(self):
        for line in self:
            qty = line._get_sell_quantity() or 0.0
            line.price_unit_sell = (line.price_gross / qty) if qty else line.price_gross


class InomCostMaterialLine(models.Model):
    _name = 'inom.cost.material.line'
    _description = 'Job Cost Material Line'
    _inherit = ['inom.cost.line.markup.mixin']
    _order = 'sequence, id'

    sequence = fields.Integer(default=10)
    estimate_id = fields.Many2one('inom.cost.estimate', string='Estimate',
                                  required=True, ondelete='cascade')
    currency_id = fields.Many2one(related='estimate_id.currency_id', string='Currency')
    company_id = fields.Many2one(related='estimate_id.company_id', string='Company',
                                 store=True, index=True)
    product_id = fields.Many2one('product.product', string='Product')
    rate_card_id = fields.Many2one(
        'inom.rate.card', string='Rate Card',
        default=lambda self: self.env.context.get('default_rate_card_id'))
    name = fields.Char(string='Description', required=True)
    use_takeoff = fields.Boolean(
        string='Use Takeoff',
        help='Derive the quantity from a measurement sheet instead of typing '
             'it in.')
    takeoff_line_ids = fields.One2many('inom.cost.takeoff.line',
                                       'material_line_id',
                                       string='Measurements', copy=True)
    takeoff_count = fields.Integer(compute='_compute_takeoff_count')
    quantity = fields.Float(string='Quantity', compute='_compute_quantity',
                            store=True, readonly=False)
    uom_id = fields.Many2one('uom.uom', string='Unit of Measure')
    price_unit = fields.Float(string='Unit Cost')
    price_subtotal = fields.Monetary(string='Cost Subtotal', compute='_compute_subtotal',
                                     store=True, currency_field='currency_id')
    price_gross = fields.Monetary(string='Price Before Discount',
                                  compute='_compute_price_sell',
                                  store=True, currency_field='currency_id')
    price_sell = fields.Monetary(string='Selling Price', compute='_compute_price_sell',
                                 store=True, currency_field='currency_id')
    price_unit_sell = fields.Monetary(
        string='Unit Price', compute='_compute_price_unit_sell',
        currency_field='currency_id',
        help='Marked-up price per unit. Shown to the customer; cost never is.')

    @api.depends('takeoff_line_ids.quantity_signed')
    def _compute_takeoff_count(self):
        for line in self:
            line.takeoff_count = len(line.takeoff_line_ids)

    @api.depends('use_takeoff', 'takeoff_line_ids.quantity_signed')
    def _compute_quantity(self):
        """Takeoff wins when it is switched on; otherwise leave what was typed."""
        for line in self:
            if line.use_takeoff:
                line.quantity = sum(
                    line.takeoff_line_ids.mapped('quantity_signed'))
            elif not line.quantity:
                line.quantity = 1.0

    def action_open_takeoff(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Measurement Sheet'),
            'res_model': 'inom.cost.material.line',
            'res_id': self.id,
            'view_mode': 'form',
            'view_id': self.env.ref(
                'inom_job_cost_estimation.view_inom_material_line_form').id,
            'target': 'new',
        }

    @api.onchange('product_id', 'rate_card_id')
    def _onchange_product_id(self):
        for line in self:
            if line.product_id:
                if not line.name:
                    line.name = line.product_id.display_name
                line.uom_id = line.product_id.uom_id
                card = line.rate_card_id or line.estimate_id.rate_card_id
                rate = card.rate_for_product(line.product_id) if card else None
                line.price_unit = rate if rate is not None else line.product_id.standard_price

    def _get_sell_quantity(self):
        self.ensure_one()
        return self.quantity or 0.0

    @api.depends('quantity', 'price_unit')
    def _compute_subtotal(self):
        for line in self:
            line.price_subtotal = line.quantity * line.price_unit



class InomCostLabourLine(models.Model):
    _name = 'inom.cost.labour.line'
    _description = 'Job Cost Manpower Line'
    _inherit = ['inom.cost.line.markup.mixin']
    _order = 'sequence, id'

    sequence = fields.Integer(default=10)
    estimate_id = fields.Many2one('inom.cost.estimate', string='Estimate',
                                  required=True, ondelete='cascade')
    currency_id = fields.Many2one(related='estimate_id.currency_id', string='Currency')
    company_id = fields.Many2one(related='estimate_id.company_id', string='Company',
                                 store=True, index=True)
    employee_id = fields.Many2one('hr.employee', string='Employee')
    job_id = fields.Many2one('hr.job', string='Job Position')
    name = fields.Char(string='Role / Description', required=True)
    quantity = fields.Float(string='No. of Persons', default=1.0)
    hours = fields.Float(string='Hours', default=1.0)
    rate_card_id = fields.Many2one(
        'inom.rate.card', string='Rate Card',
        default=lambda self: self.env.context.get('default_rate_card_id'))
    price_unit = fields.Float(string='Rate / Hour')
    price_subtotal = fields.Monetary(string='Cost Subtotal', compute='_compute_subtotal',
                                     store=True, currency_field='currency_id')
    price_gross = fields.Monetary(string='Price Before Discount',
                                  compute='_compute_price_sell',
                                  store=True, currency_field='currency_id')
    price_sell = fields.Monetary(string='Selling Price', compute='_compute_price_sell',
                                 store=True, currency_field='currency_id')
    price_unit_sell = fields.Monetary(
        string='Unit Price', compute='_compute_price_unit_sell',
        currency_field='currency_id',
        help='Marked-up price per unit. Shown to the customer; cost never is.')

    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        for line in self:
            if not line.employee_id:
                continue
            line.job_id = line.employee_id.job_id
            if not line.name:
                line.name = line.employee_id.job_title or line.employee_id.display_name
            # hourly_cost is provided by hr_timesheet, which may not be installed.
            if 'hourly_cost' in line.employee_id._fields:
                rate = line.employee_id.hourly_cost
                if rate:
                    line.price_unit = rate

    @api.onchange('job_id')
    def _onchange_job_id(self):
        for line in self:
            if line.job_id and not line.name:
                line.name = line.job_id.name

    @api.onchange('name', 'rate_card_id')
    def _onchange_labour_rate_card(self):
        for line in self:
            card = line.rate_card_id or line.estimate_id.rate_card_id
            if card and line.name:
                rate = card.rate_for_labour(line.name)
                if rate is not None:
                    line.price_unit = rate

    def _get_sell_quantity(self):
        self.ensure_one()
        return (self.quantity or 0.0) * (self.hours or 0.0)

    @api.depends('quantity', 'hours', 'price_unit')
    def _compute_subtotal(self):
        for line in self:
            line.price_subtotal = line.quantity * line.hours * line.price_unit



class InomCostOverheadLine(models.Model):
    _name = 'inom.cost.overhead.line'
    _description = 'Job Cost Indirect / Overhead Line'
    _inherit = ['inom.cost.line.markup.mixin']
    _order = 'sequence, id'

    sequence = fields.Integer(default=10)
    estimate_id = fields.Many2one('inom.cost.estimate', string='Estimate',
                                  required=True, ondelete='cascade')
    currency_id = fields.Many2one(related='estimate_id.currency_id', string='Currency')
    company_id = fields.Many2one(related='estimate_id.company_id', string='Company',
                                 store=True, index=True)
    name = fields.Char(string='Description', required=True)
    amount = fields.Monetary(string='Amount', currency_field='currency_id')
    price_subtotal = fields.Monetary(related='amount', string='Cost Subtotal',
                                     currency_field='currency_id')
    price_gross = fields.Monetary(string='Price Before Discount',
                                  compute='_compute_price_sell',
                                  store=True, currency_field='currency_id')
    price_sell = fields.Monetary(string='Selling Price', compute='_compute_price_sell',
                                 store=True, currency_field='currency_id')
    price_unit_sell = fields.Monetary(
        string='Unit Price', compute='_compute_price_unit_sell',
        currency_field='currency_id',
        help='Marked-up price per unit. Shown to the customer; cost never is.')



class InomCostEquipmentLine(models.Model):
    """Plant and equipment charged to a job.

    Equipment is quoted on time, not on quantity alone: a hired excavator is
    two units for six days. Cost is therefore units x duration x rate, and the
    rate unit is stored so the printed estimate can say "per day" rather than
    leaving the customer to guess.
    """
    _name = 'inom.cost.equipment.line'
    _description = 'Job Cost Equipment Line'
    _inherit = ['inom.cost.line.markup.mixin']
    _order = 'sequence, id'

    sequence = fields.Integer(default=10)
    estimate_id = fields.Many2one('inom.cost.estimate', string='Estimate',
                                  required=True, ondelete='cascade')
    currency_id = fields.Many2one(related='estimate_id.currency_id', string='Currency')
    company_id = fields.Many2one(related='estimate_id.company_id', string='Company',
                                 store=True, index=True)
    product_id = fields.Many2one('product.product', string='Equipment')
    name = fields.Char(string='Description', required=True)
    quantity = fields.Float(string='Units', default=1.0)
    duration = fields.Float(string='Duration', default=1.0)
    rate_unit = fields.Selection([
        ('hour', 'Per Hour'),
        ('day', 'Per Day'),
        ('week', 'Per Week'),
        ('month', 'Per Month'),
    ], string='Rate Basis', required=True, default='day')
    price_unit = fields.Float(string='Rate')
    price_subtotal = fields.Monetary(string='Cost Subtotal', compute='_compute_subtotal',
                                     store=True, currency_field='currency_id')
    price_gross = fields.Monetary(string='Price Before Discount',
                                  compute='_compute_price_sell',
                                  store=True, currency_field='currency_id')
    price_sell = fields.Monetary(string='Selling Price', compute='_compute_price_sell',
                                 store=True, currency_field='currency_id')
    price_unit_sell = fields.Monetary(
        string='Unit Price', compute='_compute_price_unit_sell',
        currency_field='currency_id',
        help='Marked-up price per unit. Shown to the customer; cost never is.')

    @api.onchange('product_id')
    def _onchange_product_id(self):
        for line in self:
            if not line.product_id:
                continue
            if not line.name:
                line.name = line.product_id.display_name
            if not line.price_unit:
                line.price_unit = line.product_id.standard_price

    def _get_sell_quantity(self):
        self.ensure_one()
        return (self.quantity or 0.0) * (self.duration or 0.0)

    @api.depends('quantity', 'duration', 'price_unit')
    def _compute_subtotal(self):
        for line in self:
            line.price_subtotal = (line.quantity or 0.0) * (line.duration or 0.0) * line.price_unit

