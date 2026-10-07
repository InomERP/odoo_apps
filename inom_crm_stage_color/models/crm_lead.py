from odoo import fields, models


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    stage_color = fields.Integer(related='stage_id.color', store=True)
