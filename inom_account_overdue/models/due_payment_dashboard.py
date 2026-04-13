from odoo import models, fields, api


class DuePaymentDashboard(models.Model):
    _name = 'due.payment.dashboard'
    _description = 'Due Payment Dashboard'

    name = fields.Char(default="Due Payment Overview")

    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.company.currency_id
    )

    total_customer_due = fields.Monetary(
        string="Customer Due",
        compute="_compute_dashboard"
    )

    total_vendor_due = fields.Monetary(
        string="Vendor Due",
        compute="_compute_dashboard"
    )

    today_received = fields.Monetary(
        string="Today Total Received",
        compute="_compute_dashboard"
    )

    today_paid = fields.Monetary(
        string="Today Total Paid",
        compute="_compute_dashboard"
    )

    customer_invoice_count = fields.Integer(
        string="Customer Invoices",
        compute="_compute_dashboard"
    )

    vendor_bill_count = fields.Integer(
        string="Vendor Bills",
        compute="_compute_dashboard"
    )

    customer_partner_count = fields.Integer(
        string="Customers",
        compute="_compute_dashboard"
    )

    vendor_partner_count = fields.Integer(
        string="Vendors",
        compute="_compute_dashboard"
    )

    critical_count = fields.Integer(
        string="Critical Alerts",
        compute="_compute_dashboard"
    )

    warning_count = fields.Integer(
        string="Warning Alerts",
        compute="_compute_dashboard"
    )

    @api.depends()
    def _compute_dashboard(self):
        overdue = self.env['account.overdue']
        today = fields.Date.today()

        for rec in self:

            customer = overdue.search([
                ('move_type', '=', 'out_invoice')
            ], order="invoice_id,id")

            vendor = overdue.search([
                ('move_type', '=', 'in_invoice')
            ], order="invoice_id,id")

            # latest customer due per invoice
            latest_customer_due = {}
            for line in customer:
                latest_customer_due[line.invoice_id.id] = line.debit

            # latest vendor due per bill
            latest_vendor_due = {}
            for line in vendor:
                latest_vendor_due[line.invoice_id.id] = line.debit

            rec.total_customer_due = sum(
                latest_customer_due.values()
            )

            rec.total_vendor_due = sum(
                latest_vendor_due.values()
            )

            # today received
            today_customer = overdue.search([
                ('move_type', '=', 'out_invoice'),
                ('date', '=', today)
            ])

            # today paid
            today_vendor = overdue.search([
                ('move_type', '=', 'in_invoice'),
                ('date', '=', today)
            ])

            rec.today_received = sum(
                today_customer.mapped('credit')
            )

            rec.today_paid = sum(
                today_vendor.mapped('credit')
            )

            rec.customer_invoice_count = len(
                latest_customer_due
            )

            rec.vendor_bill_count = len(
                latest_vendor_due
            )

            rec.customer_partner_count = len(
                customer.mapped('partner_id')
            )

            rec.vendor_partner_count = len(
                vendor.mapped('partner_id')
            )

            rec.critical_count = len([
                amt for amt in latest_customer_due.values()
                if amt > 50000
            ])

            rec.warning_count = len([
                amt for amt in latest_customer_due.values()
                if 10000 < amt <= 50000
            ])
