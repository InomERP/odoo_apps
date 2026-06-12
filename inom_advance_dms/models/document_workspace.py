from odoo import models, fields


class EdmWorkspace(models.Model):
    _name = 'edm.workspace'
    _description = 'Document Workspace'

    name = fields.Char(required=True)

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company
    )