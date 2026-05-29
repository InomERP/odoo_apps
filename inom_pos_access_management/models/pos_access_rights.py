# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class PosAccessRights(models.Model):
    """POS Access Rights – per-user/employee feature toggles for the POS UI.

    Odoo-17 migration note
    ----------------------
    The original Odoo-18 implementation inherited ``pos.load.mixin`` and
    declared ``_load_pos_data_domain`` / ``_load_pos_data_fields`` directly
    on this model. Neither the mixin nor those hooks exist in Odoo 17.
    The equivalent wiring is provided on ``pos.session`` in this module via
    ``_pos_ui_models_to_load`` + ``_loader_params_pos_access_rights`` +
    ``_get_pos_ui_pos_access_rights`` — semantically identical:
    only the access rule belonging to the current user is shipped to the
    POS frontend.
    """
    _name = 'pos.access.rights'
    _description = 'POS Access Rights'
    _rec_name = 'name'
    _order = 'user_id, id'

    name = fields.Char(
        string='Rule Name',
        compute='_compute_name',
        store=True,
        readonly=False,
    )
    user_id = fields.Many2one(
        'res.users',
        string='User',
        required=True,
        ondelete='cascade',
        index=True,
        help="User to whom this POS access rule applies.",
    )
    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        ondelete='set null',
        help="Optional employee associated with this access rule.",
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
    )
    active = fields.Boolean(default=True)

    # ------------------------------------------------------------------
    # 1. Salesperson Restrictions
    # ------------------------------------------------------------------
    restrict_salesperson_orders = fields.Boolean(
        string='Salesperson can only see his orders',
        help="When enabled, the salesperson sees only the orders they created, not orders of other staff.",
    )
    restrict_salesperson_customers = fields.Boolean(
        string='Salesperson can only see his customers',
        help="When enabled, the salesperson sees only the customers they assigned/created.",
    )

    # ------------------------------------------------------------------
    # 2. Payment Access (7)
    # ------------------------------------------------------------------
    hide_payment_button = fields.Boolean(
        string='Hide Payment Button',
        help="Hides the main 'Payment' button on the POS order screen.",
    )
    restrict_payment_method = fields.Boolean(
        string='Restrict Payment Methods',
        help="Allow only selected payment methods for this user.",
    )
    restrict_payment_method_ids = fields.Many2many(
        'pos.payment.method',
        'pos_access_rights_payment_method_rel',
        'access_rights_id',
        'payment_method_id',
        string='Allowed Payment Methods',
        help="Only these payment methods will be visible to the user on the payment screen.",
    )
    hide_payment_customer_button = fields.Boolean(
        string='Hide Customer Button (Payment Screen)',
        help="Hides the customer selection button on the payment screen.",
    )
    hide_payment_validate_button = fields.Boolean(
        string='Hide Payment Validate Button',
        help="Hides the 'Validate' button on the payment screen.",
    )
    hide_payment_tip_button = fields.Boolean(
        string='Hide Payment Tip Button',
        help="Hides the tip input button on the payment screen.",
    )
    hide_payment_ship_later_button = fields.Boolean(
        string='Hide Payment Ship Later Button',
        help="Hides the 'Ship Later' option on the payment screen.",
    )
    hide_payment_invoice_button = fields.Boolean(
        string='Hide Payment Invoice Button',
        help="Hides the 'Invoice' button on the payment screen.",
    )

    # ------------------------------------------------------------------
    # 3. Order Access (3)
    # ------------------------------------------------------------------
    restrict_pos_categories = fields.Boolean(
        string='Restrict POS Categories',
        help="Hide specific POS product categories from the user.",
    )
    restrict_pos_category_ids = fields.Many2many(
        'pos.category',
        'pos_access_rights_category_rel',
        'access_rights_id',
        'category_id',
        string='Hidden POS Categories',
        help="These POS categories will be hidden from the user.",
    )
    hide_delete_order_button = fields.Boolean(
        string='Hide Delete Order Button',
        help="Prevents the user from deleting active orders.",
    )
    only_show_active_order = fields.Boolean(
        string='Only Show Active Order',
        help="User can only see/interact with their currently active order.",
    )

    # ------------------------------------------------------------------
    # 4. Customer Access (3)
    # ------------------------------------------------------------------
    hide_customer_button = fields.Boolean(
        string='Hide Customer Button',
        help="Hides the customer selection button on the main POS order screen.",
    )
    hide_create_customer_button = fields.Boolean(
        string='Hide Create Customer Button',
        help="Prevents the user from adding new customers from POS.",
    )
    hide_save_customer_button = fields.Boolean(
        string='Hide Save Customer Button',
        help="Prevents saving new/edited customer records from POS.",
    )

    # ------------------------------------------------------------------
    # 5. Numpad Access (5)
    # ------------------------------------------------------------------
    hide_numpad_buttons = fields.Boolean(
        string='Hide Numpad Buttons',
        help="Hides the entire numpad from the POS interface.",
    )
    disable_price_button = fields.Boolean(
        string='Disable Price Button',
        help="Disables the 'Price' mode on the numpad.",
    )
    disable_qty_button = fields.Boolean(
        string='Disable Qty Button',
        help="Disables the 'Qty' mode on the numpad.",
    )
    disable_discount_button = fields.Boolean(
        string='Disable Discount Button',
        help="Disables the 'Discount' mode on the numpad.",
    )
    disable_plus_minus_button = fields.Boolean(
        string='Disable (+/-) Button',
        help="Disables the plus/minus toggle button on the numpad.",
    )

    # ------------------------------------------------------------------
    # 6. Action Access (7)
    # ------------------------------------------------------------------
    hide_customer_note_button = fields.Boolean(
        string='Hide Customer Note Button',
        help="Prevents the user from adding customer notes to orders.",
    )
    hide_refund_button = fields.Boolean(
        string='Hide Refund Button',
        help="Restricts the user from processing refunds/returns.",
    )
    hide_info_button = fields.Boolean(
        string='Hide Info Button',
        help="Hides the order information/details button from the POS interface.",
    )
    hide_quotation_button = fields.Boolean(
        string='Hide Quotation Button',
        help="Prevents the user from creating or viewing quotations from POS.",
    )
    hide_fiscal_button = fields.Boolean(
        string='Hide Fiscal Button',
        help="Hides the fiscal position button on the POS order.",
    )
    hide_pricelist_button = fields.Boolean(
        string='Hide Price List Button',
        help="Hides the pricelist selection button from the POS order screen.",
    )
    hide_transfer_button = fields.Boolean(
        string='Hide Transfer Button',
        help="Prevents the user from transferring an order to another table/session.",
    )

    # ------------------------------------------------------------------
    # 7. General Access (4)
    # ------------------------------------------------------------------
    hide_close_pos_button = fields.Boolean(
        string='Hide Close POS Button',
        help="Prevents the user from closing the POS session.",
    )
    hide_backend_pos_button = fields.Boolean(
        string='Hide Backend POS Button',
        help="Hides the button to navigate back to the Odoo backend from POS.",
    )
    hide_cash_in_out_button = fields.Boolean(
        string='Hide Cash In/Out POS Button',
        help="Prevents the user from performing cash management operations.",
    )
    hide_debug_window = fields.Boolean(
        string='Hide Debug Window',
        help="Hides the debug/developer tools window from the POS interface.",
    )

    _sql_constraints = [
        ('user_id_unique',
         'UNIQUE(user_id)',
         'A POS access rule already exists for this user. Please edit the existing rule instead.'),
    ]

    # ------------------------------------------------------------------
    # Computes
    # ------------------------------------------------------------------
    @api.depends('user_id', 'employee_id')
    def _compute_name(self):
        for rec in self:
            if rec.user_id:
                rec.name = _("POS Access – %s") % rec.user_id.name
            elif rec.employee_id:
                rec.name = _("POS Access – %s") % rec.employee_id.name
            else:
                rec.name = _("POS Access Rights")

    # ------------------------------------------------------------------
    # On-change helpers
    # ------------------------------------------------------------------
    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        """If an employee with a linked user is chosen, propagate the user."""
        for rec in self:
            if rec.employee_id and rec.employee_id.user_id and not rec.user_id:
                rec.user_id = rec.employee_id.user_id

    @api.onchange('user_id')
    def _onchange_user_id(self):
        """If user has a linked employee, propagate it."""
        for rec in self:
            if rec.user_id and not rec.employee_id:
                employee = self.env['hr.employee'].search(
                    [('user_id', '=', rec.user_id.id)], limit=1
                )
                if employee:
                    rec.employee_id = employee
