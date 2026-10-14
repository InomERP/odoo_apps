from odoo import models, fields, api

class ResPartner(models.Model):
    _inherit = 'res.partner'

    # Existing customer fields
    overdue_count = fields.Integer(
        string="Overdue Entries",
        compute="_compute_overdue_count"
    )

    has_overdue = fields.Boolean(
        string="Has Overdue",
        compute="_compute_overdue_alert"
    )

    overdue_message = fields.Char(
        string="Overdue Message",
        compute="_compute_overdue_alert"
    )

    vendor_overdue_count = fields.Integer(
        string="Vendor Overdue Bills",
        compute="_compute_vendor_overdue_count"
    )

    has_vendor_overdue = fields.Boolean(
        string="Has Vendor Overdue",
        compute="_compute_vendor_overdue_alert"
    )

    vendor_overdue_message = fields.Char(
        string="Vendor Overdue Message",
        compute="_compute_vendor_overdue_alert"
    )

    # CUSTOMER
    def _compute_overdue_count(self):
        today = fields.Date.today()

        for partner in self:
            invoices = self.env['account.move'].search([
                ('partner_id', '=', partner.id),
                ('move_type', '=', 'out_invoice'),
                ('state', '=', 'posted'),
                ('invoice_date_due', '<', today),
                ('payment_state', '!=', 'paid')
            ])

            partner.overdue_count = sum(invoices.mapped('amount_residual'))

    @api.depends('overdue_count')
    def _compute_overdue_alert(self):
        today = fields.Date.today()

        for partner in self:
            invoices = self.env['account.move'].search([
                ('partner_id', '=', partner.id),
                ('move_type', '=', 'out_invoice'),
                ('state', '=', 'posted'),
                ('invoice_date_due', '<', today),
                ('payment_state', '!=', 'paid')
            ])

            total_due = sum(invoices.mapped('amount_residual'))

            if total_due > 0:
                partner.has_overdue = True
                partner.overdue_message = (
                    f"⚠ This customer has overdue pending payment of {total_due}"
                )
            else:
                partner.has_overdue = False
                partner.overdue_message = False

     # VENDOR 
    def _compute_vendor_overdue_count(self):
        today = fields.Date.today()

        for partner in self:
            bills = self.env['account.move'].search([
                ('partner_id', '=', partner.id),
                ('move_type', '=', 'in_invoice'),
                ('state', '=', 'posted'),
                ('invoice_date_due', '<', today),
                ('payment_state', '!=', 'paid')
            ])

            partner.vendor_overdue_count = sum(
                bills.mapped('amount_residual')
            )

    @api.depends('vendor_overdue_count')
    def _compute_vendor_overdue_alert(self):
        today = fields.Date.today()

        for partner in self:
            bills = self.env['account.move'].search([
                ('partner_id', '=', partner.id),
                ('move_type', '=', 'in_invoice'),
                ('state', '=', 'posted'),
                ('invoice_date_due', '<', today),
                ('payment_state', '!=', 'paid')
            ])

            total_due = sum(bills.mapped('amount_residual'))

            if total_due > 0:
                partner.has_vendor_overdue = True
                partner.vendor_overdue_message = (
                    f"⚠ This vendor has overdue bill payment of {total_due}"
                )
            else:
                partner.has_vendor_overdue = False
                partner.vendor_overdue_message = False

    # CUSTOMER SMART BUTTON ACTION
    def action_view_overdue(self):
        self.ensure_one()
        today = fields.Date.today()

        return {
            'name': 'Customer Overdue Invoices',
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [
                ('partner_id', '=', self.id),
                ('move_type', '=', 'out_invoice'),
                ('state', '=', 'posted'),
                ('invoice_date_due', '<', today),
                ('payment_state', '!=', 'paid')
            ],
            'target': 'current',
        }

    # VENDOR SMART BUTTON ACTION
    def action_view_vendor_overdue(self):
        self.ensure_one()
        today = fields.Date.today()

        return {
            'name': 'Vendor Overdue Bills',
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [
                ('partner_id', '=', self.id),
                ('move_type', '=', 'in_invoice'),
                ('state', '=', 'posted'),
                ('invoice_date_due', '<', today),
                ('payment_state', '!=', 'paid')
            ],
            'target': 'current',
        }