from odoo import models, fields


class EdmDocumentRequestWizard(models.TransientModel):
    _name = 'edm.document.request.wizard'
    _description = 'Document Request Wizard'

    requested_to = fields.Many2one('res.users', string='Assigned To', required=True)
    workspace_id = fields.Many2one('edm.workspace', string='Workspace', required=True)
    document_id = fields.Many2one('edm.document', string='Document')
    note = fields.Text(string='Instructions', required=True)
    deadline = fields.Date(string='Due Date')

    def action_create_request(self):
        self.ensure_one()

        request = self.env['edm.document.request'].create({
            'name': self.note[:50] or 'Document Request',
            'requested_by': self.env.user.id,
            'requested_to': self.requested_to.id,
            'workspace_id': self.workspace_id.id,
            'document_id': self.document_id.id if self.document_id else False,
            'note': self.note,
            'state': 'requested',
            'deadline': self.deadline,
        })


        return {
            'type': 'ir.actions.act_window',
            'name': 'Document Request',
            'res_model': 'edm.document.request',
            'res_id': request.id,
            'view_mode': 'form',
            'target': 'current',
        }