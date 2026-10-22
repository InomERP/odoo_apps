from odoo import fields, models, tools


class PropertyRentInvoiceReport(models.Model):
    """ One line per posted rent invoice or credit note, read straight from accounting. """
    _name = 'property.rent.invoice.report'
    _description = 'Rental Income Report'
    _auto = False
    _order = 'invoice_date desc, id desc'
    _rec_name = 'move_id'

    move_id = fields.Many2one('account.move', string='Invoice', readonly=True)
    move_type = fields.Selection(
        selection=[('out_invoice', 'Invoice'), ('out_refund', 'Credit Note')], string='Type', readonly=True,
    )
    invoice_date = fields.Date(readonly=True)
    invoice_date_due = fields.Date(string='Due Date', readonly=True)
    company_id = fields.Many2one('res.company', readonly=True)
    currency_id = fields.Many2one('res.currency', string='Currency', readonly=True)
    property_id = fields.Many2one('property.property', readonly=True)
    owner_id = fields.Many2one('res.partner', string='Owner', readonly=True)
    tenant_id = fields.Many2one('res.partner', string='Tenant', readonly=True)
    contract_id = fields.Many2one('property.rental.contract', string='Rental Contract', readonly=True)
    payment_state = fields.Selection(
        selection=lambda self: self.env['account.move']._fields['payment_state'].selection,
        readonly=True,
    )
    amount_invoiced = fields.Monetary(string='Invoiced (Untaxed)', readonly=True, aggregator='sum')
    amount_total = fields.Monetary(string='Invoiced (Total)', readonly=True, aggregator='sum')
    amount_paid = fields.Monetary(string='Paid', readonly=True, aggregator='sum')
    amount_due = fields.Monetary(string='Outstanding', readonly=True, aggregator='sum')
    is_overdue = fields.Boolean(string='Overdue', readonly=True)
    days_overdue = fields.Integer(readonly=True, aggregator='max')

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(f"""
            CREATE OR REPLACE VIEW {self._table} AS (
                SELECT
                    m.id AS id,
                    m.id AS move_id,
                    m.move_type AS move_type,
                    m.invoice_date AS invoice_date,
                    m.invoice_date_due AS invoice_date_due,
                    m.company_id AS company_id,
                    c.currency_id AS currency_id,
                    m.property_id AS property_id,
                    p.owner_id AS owner_id,
                    m.partner_id AS tenant_id,
                    m.property_rental_contract_id AS contract_id,
                    m.payment_state AS payment_state,
                    m.amount_untaxed_signed AS amount_invoiced,
                    m.amount_total_signed AS amount_total,
                    m.amount_total_signed - m.amount_residual_signed AS amount_paid,
                    m.amount_residual_signed AS amount_due,
                    (m.move_type = 'out_invoice' AND m.payment_state IN ('not_paid', 'partial')
                        AND m.invoice_date_due < CURRENT_DATE) AS is_overdue,
                    CASE WHEN m.move_type = 'out_invoice' AND m.payment_state IN ('not_paid', 'partial')
                              AND m.invoice_date_due < CURRENT_DATE
                         THEN CURRENT_DATE - m.invoice_date_due ELSE 0 END AS days_overdue
                FROM account_move m
                JOIN res_company c ON c.id = m.company_id
                LEFT JOIN property_property p ON p.id = m.property_id
                WHERE m.property_rental_move_kind = 'rent'
                  AND m.state = 'posted'
                  AND m.move_type IN ('out_invoice', 'out_refund')
            )
        """)
