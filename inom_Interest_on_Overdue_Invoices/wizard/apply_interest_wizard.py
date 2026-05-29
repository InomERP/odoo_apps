# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class InomApplyInterestWizard(models.TransientModel):
    _name = 'inom.apply.interest.wizard'
    _description = 'Apply Overdue Interest Wizard'

    invoice_id = fields.Many2one('account.move', string='Invoice', required=True)
    mode = fields.Char(default='apply')  # 'preview' or 'apply'

    # Source info
    partner_id = fields.Many2one('res.partner', string='Customer',
                                 related='invoice_id.partner_id', readonly=True)
    company_id = fields.Many2one('res.company', string='Company',
                                 related='invoice_id.company_id', readonly=True)

    # Dates
    calculation_date = fields.Date(string='Calculation Date', default=fields.Date.today)
    invoice_date = fields.Date(related='invoice_id.invoice_date', readonly=True)
    due_date = fields.Date(related='invoice_id.invoice_date_due', readonly=True)

    # Overdue analysis
    days_overdue = fields.Integer(string='Days Overdue', readonly=True)
    days_after_grace = fields.Integer(string='Days After Grace', readonly=True)
    interest_rule_id = fields.Many2one('overdue.interest.rule', string='Interest Rule', readonly=True)

    # Interest calculation
    base_amount = fields.Monetary(string='Principal Amount', readonly=True,
                                   currency_field='currency_id')
    calculated_interest = fields.Monetary(string='Calculated Interest', readonly=True,
                                           currency_field='currency_id')
    final_interest = fields.Monetary(string='Final Interest', readonly=True,
                                      currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', related='invoice_id.currency_id')

    # Breakdown
    calculation_breakdown = fields.Text(string='Interest Calculation Breakdown', readonly=True)

    # Action / Output type
    output_type = fields.Selection([
        ('journal_entry', 'Create Journal Entry'),
        ('debit_note', 'Create Debit Note (Draft)'),
    ], string='Action', default='journal_entry')

    # Status
    state = fields.Selection([
        ('calculated', 'Calculated'),
        ('applied', 'Applied'),
    ], default='calculated')

    success_message = fields.Char(string='Message', readonly=True)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        invoice_id = self.env.context.get('default_invoice_id')
        p = self.env['ir.config_parameter'].sudo()
        # Output type from settings. IMPORTANT: fall back to 'debit_note' (the
        # same default used by the settings field and by the engine's
        # _get_settings). A 'journal_entry' default here produced a bare
        # accounting entry with NO product line and NO Overdue Interest tab
        # (that tab is invisible for move_type != 'out_invoice'). Defaulting to
        # 'debit_note' creates an out_invoice that shows the interest product
        # line and the Overdue Interest tab.
        output_type = p.get_param('inom_interest.overdue_output_type') or 'debit_note'
        res['output_type'] = output_type
        if invoice_id:
            invoice = self.env['account.move'].browse(invoice_id)
            vals = self.env['inom.interest.history']._evaluate_invoice(invoice)
            if vals:
                res.update({
                    'invoice_id': invoice_id,
                    'days_overdue': vals.get('days_overdue', 0),
                    'days_after_grace': vals.get('days_after_grace', 0),
                    'interest_rule_id': vals.get('rule_id'),
                    'base_amount': vals.get('base_amount', 0),
                    'calculated_interest': vals.get('calculated_interest', 0),
                    'final_interest': vals.get('final_interest', 0),
                    'calculation_breakdown': vals.get('calculation_breakdown', ''),
                    'success_message': _("Interest Calculated Successfully"),
                })
        return res

    def action_recalculate(self):
        self.ensure_one()
        invoice = self.invoice_id
        vals = self.env['inom.interest.history']._evaluate_invoice(invoice)
        if not vals:
            raise UserError(_("No overdue interest is applicable for this invoice."))
        self.write({
            'days_overdue': vals.get('days_overdue', 0),
            'days_after_grace': vals.get('days_after_grace', 0),
            'interest_rule_id': vals.get('rule_id'),
            'base_amount': vals.get('base_amount', 0),
            'calculated_interest': vals.get('calculated_interest', 0),
            'final_interest': vals.get('final_interest', 0),
            'calculation_breakdown': vals.get('calculation_breakdown', ''),
            'calculation_date': fields.Date.today(),
        })
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'inom.apply.interest.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_apply_interest(self):
        self.ensure_one()
        History = self.env['inom.interest.history']

        settings = History._get_settings()
        settings['output_type'] = self.output_type
        settings['enabled'] = True

        rec = History._upsert_for_invoice(self.invoice_id, settings=settings)
        if not rec:
            raise UserError(_("No overdue interest is applicable."))

        if self.output_type == 'journal_entry':
            move = rec._create_journal_entry(settings)
            move.action_post()
        else:
            move = rec._create_debit_note(settings)

        rec.write({'status': 'applied', 'move_id': move.id})

        return {
            'type': 'ir.actions.act_window',
            'name': _("Draft Invoice (Interest on %s)") % self.invoice_id.name,
            'res_model': 'account.move',
            'res_id': move.id,
            'view_mode': 'form',
            'views': [(False, 'form')],
            'target': 'current',
        }