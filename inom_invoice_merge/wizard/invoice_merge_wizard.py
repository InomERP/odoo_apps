from odoo import models, fields, _
from odoo.exceptions import UserError


class InvoiceMergeWizard(models.TransientModel):
    _name = "invoice.merge.wizard"
    _description = "Invoice Merge Wizard"

    merge_action = fields.Selection(
        [
            ('keep', 'Keep others'),
            ('cancel', 'Cancel others'),
        ],
        string="Merge Action",
        required=True,
        default='keep',
        
    )

    partner_id = fields.Many2one('res.partner', string="Customer", readonly=True)
    invoice_ids = fields.Many2many('account.move', string="Selected Invoices", readonly=True)
    merge_to_existing = fields.Boolean(string="Merge to Existing")
    target_invoice_id = fields.Many2one(
        'account.move',
        string="Target Invoice",
        domain="[('id', 'in', invoice_ids), ('state', '=', 'draft')]"
    )

    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        invoices = self.env["account.move"].browse(
            self.env.context.get("active_ids", [])
        )

        if invoices:
            res["invoice_ids"] = [(6, 0, invoices.ids)]
            res["partner_id"] = invoices[0].partner_id.id

        return res

    def action_merge_invoices(self):
        invoices = self.env["account.move"].browse(
            self.env.context.get("active_ids", [])
        )

        if len(invoices) < 2:
            raise UserError(_("Select at least two invoices."))

        partner = invoices[0].partner_id
        move_type = invoices[0].move_type
        currency = invoices[0].currency_id
        company = invoices[0].company_id
        
        for inv in invoices:
            if inv.state != "draft":
                raise UserError(_("Only draft invoices can be merged."))
            if inv.partner_id != partner:
                raise UserError(_("Invoices must have same partner."))
            if inv.move_type != move_type:
                raise UserError(_("Invoices must have same type."))
            if inv.currency_id != currency:
                raise UserError(_("Invoices must have same currency."))
            if inv.company_id != company:
                raise UserError(_("Invoices must belong to same company."))

        if self.merge_to_existing:
            
            if not self.target_invoice_id:
                raise UserError(_("Please select a target invoice."))

            target_invoice = self.target_invoice_id
            other_invoices = invoices - target_invoice

            for inv in other_invoices:
                for line in inv.invoice_line_ids:
                    line.copy({"move_id": target_invoice.id})

            if self.merge_action == 'cancel':
                other_invoices.button_cancel()

            return {
                "type": "ir.actions.act_window",
                "res_model": "account.move",
                "res_id": target_invoice.id,
                "view_mode": "form",
                "target": "current",
            }        

        new_invoice = self.env["account.move"].create({
            "move_type": move_type,
            "partner_id": partner.id,
            "currency_id": currency.id,
            "company_id": company.id,
            "payment_reference": "Merged (%s)" % ", ".join(invoices.mapped("name")),
        })

        for inv in invoices:
            for line in inv.invoice_line_ids:
                line.copy({"move_id": new_invoice.id})

        if self.merge_action in ['cancel']:
            invoices.button_cancel()

        return {
            "type": "ir.actions.act_window",
            "res_model": "account.move",
            "res_id": new_invoice.id,
            "view_mode": "form",
            "target": "current",
        }
