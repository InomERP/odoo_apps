from odoo import models, fields
from odoo.exceptions import UserError


class EdmUploadDocumentWizard(models.TransientModel):
    _name = 'edm.upload.document.wizard'
    _description = 'Upload Document Wizard'

    name = fields.Char(string='Document Name', required=True)
    file = fields.Binary(string='File', required=True)
    file_name = fields.Char(string='File Name')
    workspace_id = fields.Many2one('edm.workspace', string='Workspace', required=True)
    is_favorite = fields.Boolean(string='Favorite')

    def action_upload_document(self):
        self.env['edm.document'].create({
            'name': self.name,
            'file': self.file,
            'file_name': self.file_name,
            'workspace_id': self.workspace_id.id,
            'owner_id': self.env.user.id,
            'is_favorite': self.is_favorite,
            'document_type': 'file',
        })
        return {'type': 'ir.actions.act_window_close'}


class EdmMultiUploadDocumentWizard(models.TransientModel):
    _name = 'edm.multi.upload.document.wizard'
    _description = 'Bulk Upload Document Wizard'

    workspace_id = fields.Many2one('edm.workspace', string='Workspace', required=True)
    is_favorite = fields.Boolean(string='Favorite')
    attachment_ids = fields.Many2many('ir.attachment', string='Files', required=True)

    def action_multi_upload_document(self):
        for attachment in self.attachment_ids:
            self.env['edm.document'].create({
                'name': attachment.name,
                'file': attachment.datas,
                'file_name': attachment.name,
                'workspace_id': self.workspace_id.id,
                'owner_id': self.env.user.id,
                'is_favorite': self.is_favorite,
                'document_type': 'file',
            })
        return {'type': 'ir.actions.act_window_close'}


class EdmAddUrlWizard(models.TransientModel):
    _name = 'edm.add.url.wizard'
    _description = 'Add Link Wizard'

    name = fields.Char(string='Name', required=True)
    url = fields.Char(string='URL', required=True)
    workspace_id = fields.Many2one('edm.workspace', string='Workspace', required=True)

    def action_add_url(self):
        self.env['edm.document'].create({
            'name': self.name,
            'url': self.url,
            'workspace_id': self.workspace_id.id,
            'owner_id': self.env.user.id,
            'document_type': 'url',
        })
        return {'type': 'ir.actions.act_window_close'}


class EdmDocumentVersionWizard(models.TransientModel):
    _name = 'edm.document.version.wizard'
    _description = 'Upload New Document Version'

    document_id = fields.Many2one('edm.document', string='Document', required=True)
    file = fields.Binary(string='New File', required=True)
    file_name = fields.Char(string='File Name')

    def action_upload_new_version(self):
        self.ensure_one()
        document = self.document_id

        if not self.file:
            raise UserError("Please upload a new file.")

        old_version = document.version_no or 1

        if document.file:
            self.env['edm.document.version'].create({
                'document_id': document.id,
                'version_no': old_version,
                'file': document.file,
                'file_name': document.file_name or document.name,
                'uploaded_by': self.env.user.id,
            })

        new_name = self.file_name or document.file_name or document.name

        document.write({
            'file': self.file,
            'file_name': new_name,
            'name': new_name,
            'version_no': old_version + 1,
        })

        document.message_post(body="New document version uploaded.")

        return {
            'type': 'ir.actions.act_window',
            'name': 'Document',
            'res_model': 'edm.document',
            'res_id': document.id,
            'view_mode': 'form',
            'target': 'current',
        }
