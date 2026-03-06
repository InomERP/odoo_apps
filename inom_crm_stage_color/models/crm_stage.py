from odoo import models, fields

class CrmStage(models.Model):
    _inherit = "crm.stage"

    color = fields.Integer("Color")