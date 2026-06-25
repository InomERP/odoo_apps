from odoo import models, fields, api


class HealthcarePosPaymentMethod(models.Model):
    """Tender types accepted at a Healthcare POS terminal (Cash, Card, UPI,
    Bank, Insurance ...). Company-scoped so each branch can expose its own."""

    _name = 'healthcare.pos.payment.method'
    _description = 'Healthcare POS Payment Method'
    _order = 'sequence, name'

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)

    method_type = fields.Selection([
        ('cash', 'Cash'),
        ('card', 'Card'),
        ('upi', 'UPI'),
        ('bank', 'Bank Transfer'),
        ('insurance', 'Insurance'),
        ('other', 'Other'),
    ], default='cash', required=True)

    # Cash methods participate in the opening/closing cash control of a session.
    is_cash = fields.Boolean(compute='_compute_is_cash', store=True)
    icon = fields.Char(default='money', help="FontAwesome icon name without 'fa-' prefix.")

    company_id = fields.Many2one(
        'res.company', string='Company',
        default=lambda self: self.env.company)

    @api.depends('method_type')
    def _compute_is_cash(self):
        for rec in self:
            rec.is_cash = rec.method_type == 'cash'
