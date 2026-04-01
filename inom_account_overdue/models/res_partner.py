from odoo import models, fields, api

class ResPartner(models.Model):
    _inherit = 'res.partner'

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

    # BUTTON ACTION
    def action_view_overdue(self):

            return {
                'name': 'Overdue Entries',
                'type': 'ir.actions.act_window',
                'res_model': 'account.overdue',
                'view_mode': 'list,form',
                'domain': [('partner_id', '=', self.id)],
                'target': 'current',
            }