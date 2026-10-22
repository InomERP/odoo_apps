from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    rental_require_tenant_identity = fields.Boolean(
        related='company_id.rental_require_tenant_identity', readonly=False,
    )
    rental_require_lease_approval = fields.Boolean(
        related='company_id.rental_require_lease_approval', readonly=False,
    )
    rental_expiry_notice_days = fields.Integer(
        related='company_id.rental_expiry_notice_days', readonly=False,
    )
    rental_enquiry_followup_days = fields.Integer(
        related='company_id.rental_enquiry_followup_days', readonly=False,
    )
    rental_rent_due_notice_days = fields.Integer(related='company_id.rental_rent_due_notice_days', readonly=False)
    rental_enquiry_pending_days = fields.Integer(related='company_id.rental_enquiry_pending_days', readonly=False)
    rental_sale_booking_product_id = fields.Many2one(
        related='company_id.rental_sale_booking_product_id', readonly=False,
    )
    rental_sale_product_id = fields.Many2one(
        related='company_id.rental_sale_product_id', readonly=False,
    )
    rental_rent_product_id = fields.Many2one(related='company_id.rental_rent_product_id', readonly=False)
    rental_deposit_product_id = fields.Many2one(related='company_id.rental_deposit_product_id', readonly=False)
    rental_deposit_deduction_product_id = fields.Many2one(
        related='company_id.rental_deposit_deduction_product_id', readonly=False,
    )
    rental_journal_id = fields.Many2one(related='company_id.rental_journal_id', readonly=False)
    rental_auto_post_invoices = fields.Boolean(related='company_id.rental_auto_post_invoices', readonly=False)
    rental_invoice_advance_days = fields.Integer(related='company_id.rental_invoice_advance_days', readonly=False)
    rental_deposit_account_warning = fields.Boolean(compute='_compute_rental_deposit_account_warning')

    @api.depends('company_id', 'rental_deposit_product_id')
    def _compute_rental_deposit_account_warning(self):
        for settings in self:
            product = settings.rental_deposit_product_id or self.env.ref(
                'inom_rental_management.product_security_deposit', raise_if_not_found=False)
            account = product and product.with_company(settings.company_id)._get_product_accounts()['income']
            settings.rental_deposit_account_warning = bool(product) and not (
                account and account.account_type.startswith('liability')
            )
