# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError

APPROVER_GROUP = 'inom_stock_adjust_control.group_stock_adjust_approver'


class StockQuant(models.Model):
    _name = 'stock.quant'
    _inherit = ['stock.quant', 'mail.thread', 'mail.activity.mixin']

    adjust_approval_state = fields.Selection(
        selection=[
            ('no_need', 'No Approval'),
            ('to_approve', 'To Approve'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected'),
        ],
        string='Approval Status',
        default='no_need',
        copy=False,
        index=True,
        tracking=True,
    )
    adjust_currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        compute='_compute_adjust_currency',
    )
    adjust_preview_value = fields.Monetary(
        string='Financial Impact',
        compute='_compute_adjust_preview_value',
        currency_field='adjust_currency_id',
        help='Estimated value impact of the current counted quantity: the '
             'difference multiplied by the product cost.',
    )
    adjust_pending_qty = fields.Float(
        string='Submitted Quantity',
        copy=False,
        help='Counted quantity captured when the approval was requested.',
    )
    adjust_diff_qty = fields.Float(
        string='Submitted Difference',
        copy=False,
        help='Quantity difference captured when the approval was requested.',
    )
    adjust_value_impact = fields.Monetary(
        string='Value Impact',
        currency_field='adjust_currency_id',
        copy=False,
        help='Value impact captured when the approval was requested.',
    )
    adjust_requester_id = fields.Many2one(
        'res.users',
        string='Requested By',
        copy=False,
    )
    adjust_request_date = fields.Datetime(
        string='Requested On',
        copy=False,
    )
    adjust_approver_id = fields.Many2one(
        'res.users',
        string='Decided By',
        copy=False,
    )
    adjust_reject_reason = fields.Text(
        string='Rejection Reason',
        copy=False,
    )

    # ------------------------------------------------------------------
    # Compute
    # ------------------------------------------------------------------
    def _compute_adjust_currency(self):
        for quant in self:
            company = quant.company_id or self.env.company
            quant.adjust_currency_id = company.currency_id

    @api.depends('inventory_quantity', 'quantity', 'inventory_quantity_set',
                 'product_id.standard_price')
    def _compute_adjust_preview_value(self):
        for quant in self:
            if quant.inventory_quantity_set:
                diff = quant.inventory_quantity - quant.quantity
                quant.adjust_preview_value = diff * (quant.product_id.standard_price or 0.0)
            else:
                quant.adjust_preview_value = 0.0

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _adjust_is_approver(self):
        return self.env.user.has_group(APPROVER_GROUP)

    def _adjust_get_approver_users(self):
        """Return the users belonging to the approver group.

        The relation field name on res.groups changed across versions, so it
        is resolved defensively to stay compatible.
        """
        group = self.env.ref(APPROVER_GROUP, raise_if_not_found=False)
        if not group:
            return self.env['res.users']
        if 'users' in group._fields:
            return group.users
        if 'user_ids' in group._fields:
            return group.user_ids
        return self.env['res.users']

    def _adjust_needs_approval(self):
        """Return True when the current adjustment must be approved."""
        self.ensure_one()
        # Approvers always apply directly.
        if self._adjust_is_approver():
            return False
        # An already approved request must be applied, not resubmitted.
        if self.adjust_approval_state == 'approved':
            return False
        # Only a counted line can be submitted.
        if not self.inventory_quantity_set:
            return False
        diff = abs(self.inventory_quantity - self.quantity)
        if not diff:
            return False
        company = self.company_id or self.env.company
        if company.adjust_approval_require_all:
            return True
        qty_threshold = company.adjust_approval_qty_threshold or 0.0
        value_threshold = company.adjust_approval_value_threshold or 0.0
        # Nothing configured: preserve standard Odoo behaviour.
        if qty_threshold <= 0.0 and value_threshold <= 0.0:
            return False
        value = abs(diff * (self.product_id.standard_price or 0.0))
        over_qty = qty_threshold > 0.0 and diff >= qty_threshold
        over_value = value_threshold > 0.0 and value >= value_threshold
        return over_qty or over_value

    def _adjust_submit_for_approval(self):
        for quant in self:
            diff = quant.inventory_quantity - quant.quantity
            quant.write({
                'adjust_approval_state': 'to_approve',
                'adjust_pending_qty': quant.inventory_quantity,
                'adjust_diff_qty': diff,
                'adjust_value_impact': diff * (quant.product_id.standard_price or 0.0),
                'adjust_requester_id': self.env.user.id,
                'adjust_request_date': fields.Datetime.now(),
                'adjust_approver_id': False,
                'adjust_reject_reason': False,
            })
            quant._adjust_schedule_activity()
            quant.message_post(
                body=_('Inventory adjustment submitted for approval by %s.',
                       self.env.user.display_name)
            )

    def _adjust_schedule_activity(self):
        self.ensure_one()
        approvers = self._adjust_get_approver_users()
        for user in approvers:
            if user.id == self.env.user.id:
                continue
            self.activity_schedule(
                'mail.mail_activity_data_todo',
                user_id=user.id,
                summary=_('Inventory adjustment awaiting approval'),
                note=_('A stock adjustment for %s needs your approval.',
                       self.product_id.display_name),
            )

    def _adjust_clear_activities(self):
        self.activity_unlink(['mail.mail_activity_data_todo'])

    def _adjust_revert_count(self):
        for quant in self:
            quant.inventory_quantity_set = False

    def _adjust_notify_submitted(self):
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'warning',
                'title': _('Approval Required'),
                'message': _('The adjustment was sent for approval and has not '
                             'been applied yet.'),
                'sticky': False,
            },
        }

    # ------------------------------------------------------------------
    # Overrides
    # ------------------------------------------------------------------
    def action_apply_inventory(self):
        to_apply = self.env['stock.quant']
        to_submit = self.env['stock.quant']
        for quant in self:
            if quant._adjust_needs_approval():
                to_submit |= quant
            else:
                to_apply |= quant
        if to_submit:
            to_submit._adjust_submit_for_approval()
        result = None
        if to_apply:
            result = super(StockQuant, to_apply).action_apply_inventory()
        if result is not None:
            return result
        if to_submit:
            return to_submit._adjust_notify_submitted()
        return result

    # ------------------------------------------------------------------
    # Approval actions
    # ------------------------------------------------------------------
    def action_adjust_approve(self):
        if not self._adjust_is_approver():
            raise UserError(_('Only an Inventory Adjustment Approver can approve adjustments.'))
        approvable = self.filtered(lambda q: q.adjust_approval_state == 'to_approve')
        if not approvable:
            raise UserError(_('There is no adjustment waiting for approval in the selection.'))
        for quant in approvable:
            quant.write({
                'adjust_approval_state': 'approved',
                'adjust_approver_id': self.env.user.id,
            })
            quant._adjust_clear_activities()
            quant.message_post(
                body=_('Inventory adjustment approved by %s.', self.env.user.display_name)
            )
        # Apply the approved adjustments now.
        return approvable.action_apply_inventory()

    def action_adjust_open_reject(self):
        if not self._adjust_is_approver():
            raise UserError(_('Only an Inventory Adjustment Approver can reject adjustments.'))
        approvable = self.filtered(lambda q: q.adjust_approval_state == 'to_approve')
        if not approvable:
            raise UserError(_('There is no adjustment waiting for approval in the selection.'))
        return {
            'name': _('Reject Inventory Adjustment'),
            'type': 'ir.actions.act_window',
            'res_model': 'stock.adjust.reject.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'active_model': 'stock.quant',
                'active_ids': approvable.ids,
            },
        }
