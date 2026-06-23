# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class StockInventoryCount(models.Model):
    _name = 'stock.inventory.count'
    _description = 'Inventory Count'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    name = fields.Char(
        string='Reference',
        required=True,
        copy=False,
        readonly=True,
        index=True,
        default=lambda self: _('New'),
    )
    approver_id = fields.Many2one(
        'res.users',
        string='Approver',
        tracking=True,
        default=lambda self: self.env.user,
        help='User responsible for approving this inventory count.',
    )
    date = fields.Date(
        string='Count Date',
        required=True,
        default=fields.Date.context_today,
        tracking=True,
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
    )
    warehouse_id = fields.Many2one(
        'stock.warehouse',
        string='Warehouse',
        required=True,
        tracking=True,
        check_company=True,
    )
    allowed_location_ids = fields.Many2many(
        'stock.location',
        string='Allowed Locations',
        compute='_compute_allowed_location_ids',
        help='Technical field used to filter the location based on '
             'the selected warehouse.',
    )
    location_id = fields.Many2one(
        'stock.location',
        string='Location',
        tracking=True,
        check_company=True,
        domain="[('id', 'in', allowed_location_ids)]",
        help='Internal location to be counted. '
             'The list is filtered by the selected warehouse.',
    )
    session_type = fields.Selection(
        selection=[
            ('single', 'Single Session'),
            ('multi', 'Multi Session'),
        ],
        string='Count Type',
        required=True,
        default='single',
        tracking=True,
        help='Single Session creates one counting session.\n'
             'Multi Session allows creating multiple sessions '
             'for different users.',
    )
    use_barcode_scanner = fields.Boolean(
        string='Use Barcode Scanner',
        help='Enable barcode-driven counting for the sessions '
             'of this inventory count.',
    )
    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('in_progress', 'In Progress'),
            ('to_be_approved', 'To Be Approved'),
            ('validated', 'Validated'),
            ('rejected', 'Rejected'),
        ],
        string='Status',
        default='draft',
        required=True,
        copy=False,
        tracking=True,
    )
    product_line_ids = fields.One2many(
        'stock.inventory.count.product.line',
        'count_id',
        string='Products',
        copy=True,
    )
    count_line_ids = fields.One2many(
        'stock.inventory.count.line',
        'count_id',
        string='Inventory Count Lines',
        copy=False,
    )
    session_ids = fields.One2many(
        'stock.inventory.count.session',
        'inventory_count_id',
        string='Sessions',
        copy=False,
    )
    session_count = fields.Integer(
        string='Session Count',
        compute='_compute_session_count',
    )
    planner_id = fields.Many2one(
        'stock.inventory.count.planner',
        string='Planner',
        copy=False,
        index=True,
        help='The planner that automatically created this count, if any.',
    )
    product_count = fields.Integer(
        string='Product Count',
        compute='_compute_product_count',
    )

    @api.depends('warehouse_id')
    def _compute_allowed_location_ids(self):
        location_obj = self.env['stock.location']
        for count in self:
            domain = [('usage', '=', 'internal')]
            if count.warehouse_id:
                domain = [
                    ('id', 'child_of', count.warehouse_id.view_location_id.id),
                    ('usage', '=', 'internal'),
                ]
            count.allowed_location_ids = location_obj.search(domain)

    @api.depends('product_line_ids')
    def _compute_product_count(self):
        for count in self:
            count.product_count = len(count.product_line_ids)

    @api.depends('session_ids')
    def _compute_session_count(self):
        for count in self:
            count.session_count = len(count.session_ids)

    @api.onchange('warehouse_id')
    def _onchange_warehouse_id(self):
        # Clear the location when it no longer belongs to the chosen warehouse.
        if self.location_id and self.location_id not in self.allowed_location_ids:
            self.location_id = False

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'stock.inventory.count') or _('New')
        return super().create(vals_list)

    def unlink(self):
        for count in self:
            if count.state not in ('draft', 'rejected'):
                raise UserError(_(
                    "You can only delete inventory counts that are in "
                    "Draft or Rejected state."))
        return super().unlink()

    def action_open_create_session_wizard(self):
        self.ensure_one()
        if not self.product_line_ids:
            raise UserError(_(
                "Please add at least one product before creating a session."))
        action = self.env['ir.actions.actions']._for_xml_id(
            'inom_multi_user_inventory_count.action_create_session_wizard')
        action['context'] = {'default_count_id': self.id}
        return action

    def action_view_sessions(self):
        self.ensure_one()
        action = self.env['ir.actions.actions']._for_xml_id(
            'inom_multi_user_inventory_count.action_stock_inventory_count_session')
        action['domain'] = [('inventory_count_id', '=', self.id)]
        action['context'] = {'default_inventory_count_id': self.id}
        return action

    def _get_theoretical_qty(self, product_id, location_id):
        """Return the current system quantity for a product at a location."""
        quants = self.env['stock.quant'].search([
            ('product_id', '=', product_id),
            ('location_id', '=', location_id),
        ])
        return sum(quants.mapped('quantity'))

    def action_complete_counting(self):
        self.ensure_one()
        if self.state != 'in_progress':
            raise UserError(_(
                "Counting can only be completed for a count that is "
                "In Progress."))
        if not self.session_ids:
            raise UserError(_(
                "There are no sessions to complete for this inventory count."))
        pending_sessions = self.session_ids.filtered(
            lambda s: s.state != 'done')
        if pending_sessions:
            raise UserError(_(
                "All sessions must be submitted before completing the "
                "counting. Pending sessions: %s") % ', '.join(
                    pending_sessions.mapped('name')))

        # Aggregate submitted session lines by product and location.
        # Rejected lines are excluded: their value has been replaced by the
        # corrected line counted in the re-session.
        aggregated = {}
        for session in self.session_ids:
            for line in session.session_line_ids:
                if line.state == 'reject':
                    continue
                key = (line.product_id.id, line.location_id.id)
                data = aggregated.setdefault(
                    key, {'counted_qty': 0.0, 'mistake': False})
                data['counted_qty'] += line.counted_qty
                if line.user_calculation_mistake:
                    data['mistake'] = True

        # Rebuild the result lines (idempotent if re-run).
        self.count_line_ids.unlink()
        line_vals = []
        for (product_id, location_id), data in aggregated.items():
            theoretical = self._get_theoretical_qty(product_id, location_id)
            line_vals.append((0, 0, {
                'product_id': product_id,
                'location_id': location_id,
                'theoretical_qty': theoretical,
                'counted_qty': data['counted_qty'],
                'user_calculation_mistake': data['mistake'],
            }))
        self.write({
            'count_line_ids': line_vals,
            'state': 'to_be_approved',
        })

    # ------------------------------------------------------------------
    # Phase 4 - Count level validate / reject
    # ------------------------------------------------------------------
    def action_validate(self):
        self.ensure_one()
        if self.state != 'to_be_approved':
            raise UserError(_(
                "Only a count in the 'To Be Approved' state can be "
                "validated."))
        if not self.count_line_ids:
            raise UserError(_(
                "There are no count lines to validate."))
        # Apply each counted quantity as an inventory adjustment. Using the
        # standard inventory mode creates the corresponding stock moves.
        quant_obj = self.env['stock.quant'].with_context(inventory_mode=True)
        for line in self.count_line_ids:
            quant_obj.create({
                'product_id': line.product_id.id,
                'location_id': line.location_id.id,
                'inventory_quantity_auto_apply': line.counted_qty,
            })
        self.write({'state': 'validated'})
        self.message_post(body=_("Inventory count validated and stock "
                                 "quantities updated."))

    def action_reject(self):
        self.ensure_one()
        if self.state != 'to_be_approved':
            raise UserError(_(
                "Only a count in the 'To Be Approved' state can be "
                "rejected."))
        self.write({'state': 'rejected'})
        self.message_post(body=_("Inventory count rejected. Please add the "
                                 "reason in the chatter and recount if needed."))

    def action_reset_to_progress(self):
        self.ensure_one()
        if self.state != 'rejected':
            raise UserError(_(
                "Only a rejected count can be sent back for recounting."))
        self.write({'state': 'in_progress'})
