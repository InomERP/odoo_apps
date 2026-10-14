from odoo import models, fields

class ActivityRule(models.Model):
    _name = 'activity.rule'
    _description = 'Auto Activity Rule'

    name = fields.Char(string='Rule Name', required=True)

    model_id = fields.Many2one(
        'ir.model',
        string='Model',
        required=True,
        ondelete='cascade', 
        domain=[('model', 'in', ['sale.order', 'account.move'])]
    )

    trigger = fields.Selection([
        ('confirm', 'On Sales Order Confirm'),
        ('post', 'On Invoice Post'),
    ], string='Trigger', required=True)

    activity_type_id = fields.Many2one(
        'mail.activity.type',
        string='Activity Type',
        required=True
    )

    user_id = fields.Many2many(
        'res.users',
        string='Assigned To',
        required=True
    )



    days = fields.Integer(
        string='Due in (Days)',
        default=0
    )

    note = fields.Text(string='Activity Note')
