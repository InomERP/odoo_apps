from odoo import fields, models


class CrmStage(models.Model):
    _inherit = 'crm.stage'

    color = fields.Integer(string="Color")
