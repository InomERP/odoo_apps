from odoo import models, fields, api


class HealthcarePosPayment(models.Model):
    _name = 'healthcare.pos.payment'
    _description = 'Healthcare POS Payment'
    _order = 'id'

    order_id = fields.Many2one(
        'healthcare.pos.order', required=True, ondelete='cascade', index=True)
    payment_method_id = fields.Many2one(
        'healthcare.pos.payment.method', string='Method', required=True)
    amount = fields.Float(required=True)
    payment_date = fields.Datetime(default=fields.Datetime.now)
    is_cash = fields.Boolean(related='payment_method_id.is_cash', store=True, readonly=True)
    currency_id = fields.Many2one(
        'res.currency', related='order_id.currency_id', store=True, readonly=True)
