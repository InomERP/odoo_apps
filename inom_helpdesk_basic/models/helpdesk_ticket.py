from odoo import api, fields, models, _
from odoo.exceptions import UserError

class HelpdeskTicket(models.Model):
    _name = 'helpdesk.ticket'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Helpdesk Ticket'
    _rec_name = 'ticket_number'

    ticket_number = fields.Char(
        string="Ticket Number",
        copy=False,
        default='New'
    )

    subject = fields.Char(string="Subject")
    description = fields.Text(string="Description")
    priority = fields.Selection([
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High')
    ], default="medium", string="Priority")
    assigned_to = fields.Many2one('res.users', string="Assigned To")
    state = fields.Selection([
        ('new', 'New'),
        ('in_process', 'In process'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed')
    ], default="new", string="Ticket State", group_expand='_group_expand_states')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('ticket_number', 'New') in ('New', False, '', '0'):
                vals['ticket_number'] = self.env['ir.sequence'].next_by_code('helpdesk.ticket') or '/'
        return super().create(vals_list)

    def _group_expand_states(self, values, domain, order):
        return ['new', 'in_process', 'resolved', 'closed']

    def in_process_ticket(self):
        for res in self:
            res.state = "in_process"
            res.message_post(body="Ticket moved to In Progress")

    def resolved_ticket(self):
        for res in self:
            res.state = "resolved"
            res.message_post(body="Ticket has been resolved")

    def close_ticket(self):
        for res in self:
            res.state = "closed"
            res.message_post(body="Ticket closed")

    def action_print_ticket_report(self):
        return self.env.ref('inom_helpdesk_basic.action_helpdesk_ticket_report').report_action(self)

    def write(self, vals):
        for rec in self:
            if rec.state == 'closed':
                raise UserError(_("You cannot modify a closed ticket"))
            if 'state' in vals:
                if not self.env.user.has_group('inom_helpdesk_basic.group_helpdesk_manager'):
                    raise UserError(_("Only Helpdesk Manager can change state"))
            if 'assigned_to' in vals:
                if not self.env.user.has_group('inom_helpdesk_basic.group_helpdesk_manager'):
                    raise UserError(_("Only Helpdesk Manager can assign tickets"))
        return super().write(vals)