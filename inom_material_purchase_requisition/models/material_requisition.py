# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class MaterialRequisition(models.Model):
    _name = 'material.requisition'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Material Purchase Requisition'
    _order = 'request_date desc, id desc'

    # ------------------------------------------------------------------
    # Feature 1: core header fields
    # ------------------------------------------------------------------
    name = fields.Char(
        string='Requisition No.',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: self.env['ir.sequence'].next_by_code(
            'material.requisition'
        ) or '/',
    )
    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        required=True,
        tracking=True,
    )
    department_id = fields.Many2one(
        'hr.department',
        string='Department',
        related='employee_id.department_id',
        store=True,
        readonly=True,
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
    )
    requisition_responsible_id = fields.Many2one(
        'res.users',
        string='Requisition Responsible',
        default=lambda self: self.env.user,
        tracking=True,
    )
    request_date = fields.Date(
        string='Requisition Date',
        default=fields.Date.context_today,
        tracking=True,
    )
    received_date = fields.Date(
        string='Received Date',
        readonly=True,
        copy=False,
    )
    requisition_deadline = fields.Date(
        string='Requisition Deadline',
        tracking=True,
    )
    analytic_account_id = fields.Many2one(
        'account.analytic.account',
        string='Analytic Account',
    )
    state = fields.Selection(
        [
            ('draft', 'New'),
            ('confirm', 'Waiting Department Approval'),
            ('manager_approved', 'Waiting Manager  Approval'),
            ('user_approved', 'Approved'),
            ('done', 'Processed'),
            ('received', 'Received'),
            ('rejected', 'Rejected'),
        ],
        string='Status',
        default='draft',
        copy=False,
        tracking=True,
    )
    rejection_reason = fields.Text(
        string='Rejection Reason',
        readonly=True,
        tracking=True,
    )
    requisition_line_ids = fields.One2many(
        'material.requisition.line',
        'requisition_id',
        string='Requisition Lines',
    )

    # ------------------------------------------------------------------
    # Picking Details
    # ------------------------------------------------------------------
    picking_type_id = fields.Many2one(
        'stock.picking.type',
        string='Picking Type',
        domain="[('code', '=', 'internal'), ('company_id', '=', company_id)]",
    )
    source_location_id = fields.Many2one(
        'stock.location',
        string='Source Location',
        domain="[('usage', 'in', ('internal', 'supplier'))]",
    )
    dest_location_id = fields.Many2one(
        'stock.location',
        string='Destination Location',
        compute='_compute_dest_location_id',
        store=True,
        readonly=False,
        domain="[('usage', 'in', ('internal', 'customer'))]",
    )

    # ------------------------------------------------------------------
    # Smart buttons
    # ------------------------------------------------------------------
    picking_ids = fields.One2many(
        'stock.picking',
        'material_requisition_id',
        string='Internal Pickings',
        copy=False,
    )
    picking_count = fields.Integer(
        string='Picking Count',
        compute='_compute_picking_count',
        compute_sudo=True,
    )
    purchase_order_ids = fields.One2many(
        'purchase.order',
        'material_requisition_id',
        string='Purchase Orders',
        copy=False,
    )
    purchase_count = fields.Integer(
        string='Purchase Order Count',
        compute='_compute_purchase_count',
        compute_sudo=True,
    )

    # ------------------------------------------------------------------
    # Computes
    # ------------------------------------------------------------------
    @api.depends('employee_id')
    def _compute_dest_location_id(self):
        """Destination location priority: employee location, then department."""
        for requisition in self:
            location = False
            if requisition.employee_id.requisition_stock_location_id:
                location = requisition.employee_id.requisition_stock_location_id
            elif requisition.employee_id.department_id.requisition_stock_location_id:
                location = requisition.employee_id.department_id.requisition_stock_location_id
            requisition.dest_location_id = location

    @api.depends('state')
    def _compute_picking_count(self):
        for requisition in self:
            requisition.picking_count = self.env['stock.picking'].sudo().search_count([
                ('material_requisition_id', '=', requisition.id),
            ])

    @api.depends('state')
    def _compute_purchase_count(self):
        for requisition in self:
            requisition.purchase_count = self.env['purchase.order'].sudo().search_count([
                ('material_requisition_id', '=', requisition.id),
            ])
    # ------------------------------------------------------------------
    # Feature 7: Employee confirms / submits requisition
    # ------------------------------------------------------------------
    def action_confirm(self):
        for requisition in self:
            if not requisition.requisition_line_ids:
                raise UserError(_(
                    'You cannot confirm a requisition without any lines.'
                ))
            requisition.state = 'confirm'
            requisition._notify_department_manager()
        return True

    # ------------------------------------------------------------------
    # Feature 10 / 11: Department Manager approval / rejection
    # ------------------------------------------------------------------
    def action_manager_approve(self):
        for requisition in self:
            if requisition.state != 'confirm':
                raise UserError(_(
                    'Only requisitions waiting for department approval can be '
                    'approved by the manager.'
                ))
            requisition.state = 'manager_approved'
            requisition._notify_requisition_user()
        return True
    def action_manager_reject(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Reason For Rejection',
            'res_model': 'material.requisition.reject.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_requisition_id': self.id,
                'default_reject_type': 'manager',
            },
        }

    # ------------------------------------------------------------------
    # Feature 12 / 13: Requisition User approval / rejection
    # ------------------------------------------------------------------
    def action_user_approve(self):
        for requisition in self:
            if requisition.state != 'manager_approved':
                raise UserError(_(
                    'Only requisitions waiting for requisition user approval '
                    'can be approved.'
                ))
            requisition.state = 'user_approved'
        return True

    def action_user_reject(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Reason For Rejection',
            'res_model': 'material.requisition.reject.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_requisition_id': self.id,
                'default_reject_type': 'user',
            },
        }

    def action_reset_to_draft(self):
        for requisition in self:
            pickings = self.env['stock.picking'].sudo().search([
                ('material_requisition_id', '=', requisition.id),
            ])
            orders = self.env['purchase.order'].sudo().search([
                ('material_requisition_id', '=', requisition.id),
            ])
            pickings.write({'material_requisition_id': False})
            orders.write({'material_requisition_id': False})
            requisition.write({
                'state': 'draft',
                'rejection_reason': False,
                'received_date': False,
            })
            requisition.message_post(
                body=_('Requisition reset to Draft. Process restarted from the beginning.'),
            )
        return True

    # ------------------------------------------------------------------
    # Feature 16 / 17: Process - create Internal Picking and Purchase Orders
    # ------------------------------------------------------------------
    def action_process(self):
        for requisition in self:
            if requisition.state != 'user_approved':
                raise UserError(_(
                    'Only approved requisitions can be processed.'
                ))
            internal_lines = requisition.requisition_line_ids.filtered(
                lambda line: line.requisition_action == 'internal_picking'
            )
            purchase_lines = requisition.requisition_line_ids.filtered(
                lambda line: line.requisition_action == 'purchase_order'
            )
            if internal_lines:
                requisition._create_internal_picking(internal_lines)
            if purchase_lines:
                requisition._create_purchase_orders(purchase_lines)
            requisition.state = 'done'
        return True

    def _create_internal_picking(self, lines):
        """Create one internal transfer for all internal-picking lines."""
        self.ensure_one()
        picking_type = self.picking_type_id
        if not picking_type:
            picking_type = self.env['stock.picking.type'].search([
                ('code', '=', 'internal'),
                ('company_id', '=', self.company_id.id),
            ], limit=1)
        if not picking_type:
            raise UserError(_(
                'No internal picking type found for company %s.'
            ) % self.company_id.name)

        source_location = self.source_location_id or picking_type.default_location_src_id
        dest_location = self.dest_location_id or picking_type.default_location_dest_id
        if not source_location or not dest_location:
            raise UserError(_(
                'Please configure the source and destination locations on '
                'the Picking Details tab.'
            ))

        move_vals = []
        for line in lines:
            move_vals.append((0, 0, {
                'product_id': line.product_id.id,
                'product_uom_qty': line.product_uom_qty,
                'product_uom': line.product_uom_id.id or line.product_id.uom_id.id,
                'location_id': source_location.id,
                'location_dest_id': dest_location.id,
                'company_id': self.company_id.id,
                'description_picking': line.description or line.product_id.display_name,
            }))


        picking = self.env['stock.picking'].sudo().create({
            'picking_type_id': picking_type.id,
            'location_id': source_location.id,
            'location_dest_id': dest_location.id,
            'origin': self.name,
            'company_id': self.company_id.id,
            'material_requisition_id': self.id,
            'move_ids': move_vals,
        })
        picking.action_confirm()
        return picking

    def _create_purchase_orders(self, lines):
        """Create one purchase order per vendor for purchase-order lines."""
        self.ensure_one()
        lines_without_vendor = lines.filtered(lambda line: not line.vendor_id)
        if lines_without_vendor:
            raise UserError(_(
                'Please set a vendor on all purchase order lines before '
                'processing the requisition.'
            ))

        purchase_orders = self.env['purchase.order']
        vendors = lines.mapped('vendor_id')
        for vendor in vendors:
            vendor_lines = lines.filtered(lambda line: line.vendor_id == vendor)
            order_line_vals = []
            for line in vendor_lines:
                order_line_vals.append((0, 0, {
                    'product_id': line.product_id.id,
                    'name': line.description or line.product_id.display_name,
                    'product_qty': line.product_uom_qty,
                    'product_uom': line.product_uom_id.id or line.product_id.uom_id.id,
                    'price_unit': line.product_id.standard_price,
                    'date_planned': fields.Datetime.now(),
                }))
            order = self.env['purchase.order'].sudo().create({
                'partner_id': vendor.id,
                'origin': self.name,
                'company_id': self.company_id.id,
                'material_requisition_id': self.id,
                'order_line': order_line_vals,
            })
            purchase_orders |= order
        return purchase_orders

    # ------------------------------------------------------------------
    # Feature 18: Mark as received
    # ------------------------------------------------------------------
    def action_received(self):
        for requisition in self:
            if requisition.state != 'done':
                raise UserError(_(
                    'Only processed requisitions can be marked as received.'
                ))
            requisition.write({
                'state': 'received',
                'received_date': fields.Date.context_today(requisition),
            })
        return True

    # ------------------------------------------------------------------
    # Smart button actions
    # ------------------------------------------------------------------
    def action_view_pickings(self):
        self.ensure_one()
        action = self.env['ir.actions.actions']._for_xml_id(
            'stock.action_picking_tree_all'
        )
        pickings = self.picking_ids
        if len(pickings) > 1:
            action['domain'] = [('id', 'in', pickings.ids)]
        elif pickings:
            action['views'] = [
                (self.env.ref('stock.view_picking_form').id, 'form')
            ]
            action['res_id'] = pickings.id
        return action

    def action_view_purchase_orders(self):
        self.ensure_one()
        action = self.env['ir.actions.actions']._for_xml_id(
            'purchase.purchase_form_action'
        )
        orders = self.purchase_order_ids
        if len(orders) > 1:
            action['domain'] = [('id', 'in', orders.ids)]
        elif orders:
            action['views'] = [
                (self.env.ref('purchase.purchase_order_form').id, 'form')
            ]
            action['res_id'] = orders.id
        return action

    # ------------------------------------------------------------------
    # Feature 14: Email notifications
    # ------------------------------------------------------------------
    def _notify_department_manager(self):
        self.ensure_one()
        template = self.env.ref(
            'inom_material_purchase_requisition.mail_template_manager_approval',
            raise_if_not_found=False,
        )
        manager = self.department_id.manager_id
        if template and manager and manager.user_id:
            template.send_mail(self.id, force_send=True, email_values={
                'email_to': manager.user_id.partner_id.email,
            })

    def _notify_requisition_user(self):
        self.ensure_one()
        template = self.env.ref(
            'inom_material_purchase_requisition.mail_template_user_approval',
            raise_if_not_found=False,
        )
        user_group = self.env.ref(
            'inom_material_purchase_requisition.group_material_requisition_user',
            raise_if_not_found=False,
        )
        if template and user_group:
            recipients = user_group.users.mapped('partner_id.email')
            recipients = [email for email in recipients if email]
            if recipients:
                template.send_mail(self.id, force_send=True, email_values={
                    'email_to': ','.join(recipients),
                })