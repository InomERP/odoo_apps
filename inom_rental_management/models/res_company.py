from odoo import fields, models

RENTAL_PRODUCTS = {
    'rent': ('rental_rent_product_id', 'inom_rental_management.product_rent'),
    'deposit': ('rental_deposit_product_id', 'inom_rental_management.product_security_deposit'),
    'deduction': ('rental_deposit_deduction_product_id', 'inom_rental_management.product_deposit_deduction'),
}


class ResCompany(models.Model):
    _inherit = 'res.company'

    rental_require_tenant_identity = fields.Boolean(
        string='Require Tenant Identity Document',
        help="A rental contract can only start when its tenant has a valid identity document.",
    )
    rental_require_lease_approval = fields.Boolean(
        string='Require Lease Approval',
        help="Rental contracts must be approved by a Property Manager before they start.",
    )
    rental_expiry_notice_days = fields.Integer(
        string='Lease Expiry Notice (Days)', default=30,
        help="An activity is scheduled for the responsible person this many days before a lease ends. 0 disables it.",
    )
    rental_enquiry_followup_days = fields.Integer(
        string='Enquiry Follow-up (Days)', default=1,
        help="A follow-up activity is scheduled for the responsible salesperson this many days after a property "
             "enquiry is recorded. 0 disables it.",
    )
    rental_rent_due_notice_days = fields.Integer(
        string='Rent Due Reminder (Days)', default=3,
        help="Remind the responsible agent this many days before rent is due. 0 disables it.",
    )
    rental_enquiry_pending_days = fields.Integer(
        string='Pending Enquiry Reminder (Days)', default=3,
        help="Remind the salesperson of an open enquiry with no planned activity and no change for this many days. "
             "0 disables it.",
    )
    rental_sale_booking_product_id = fields.Many2one(
        'product.product', string='Booking Amount Product',
        help="Product used on booking amount invoices of property sales.",
    )
    rental_sale_product_id = fields.Many2one(
        'product.product', string='Property Sale Product',
        help="Product used on balance invoices of property sales.",
    )
    rental_rent_product_id = fields.Many2one(
        'product.product', string='Rent Product',
        help="Product used on rent invoices: its taxes and income account apply.",
    )
    rental_deposit_product_id = fields.Many2one(
        'product.product', string='Security Deposit Product',
        help="Product used on deposit invoices and settlements. Give it a liability account as income account "
             "to keep deposits out of rental income.",
    )
    rental_deposit_deduction_product_id = fields.Many2one(
        'product.product', string='Deposit Deduction Product',
        help="Product used for deductions kept from a deposit, such as repairs. Its income account applies.",
    )
    rental_journal_id = fields.Many2one(
        'account.journal', string='Rental Journal', check_company=True, domain="[('type', '=', 'sale')]",
        help="Sales journal for rent and deposit invoices. Leave empty to use the default sales journal.",
    )
    rental_auto_post_invoices = fields.Boolean(
        string='Post Rent Invoices Automatically',
        help="Rent and deposit invoices created by Odoo are confirmed straight away. "
             "When unticked they are left in draft for review.",
    )
    rental_invoice_advance_days = fields.Integer(
        string='Invoice Rent in Advance (Days)', default=0,
        help="Create a period's rent invoice this many days before its due date.",
    )

    def _get_rental_product(self, kind):
        """ Product configured on the company, or the module's default one. During an upgrade the
        default product may not be loaded yet: an empty recordset is returned then. """
        self.ensure_one()
        fname, xmlid = RENTAL_PRODUCTS[kind]
        return self[fname] or self.env.ref(xmlid, raise_if_not_found=False) or self.env['product.product']
