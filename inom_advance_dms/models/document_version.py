from odoo import models, fields


class EdmDocumentVersion(models.Model):
    _name = 'edm.document.version'
    _description = 'Document Version'
    _order = 'version_no desc'

    document_id = fields.Many2one(
        'edm.document',
        string='Document',
        required=True,
        ondelete='cascade'
    )

    version_no = fields.Integer(string='Version No')

    file = fields.Binary(string='File')

    file_name = fields.Char(string='File Name')

    uploaded_by = fields.Many2one(
        'res.users',
        string='Uploaded By',
        default=lambda self: self.env.user
    )

    uploaded_date = fields.Datetime(
        string='Uploaded Date',
        default=fields.Datetime.now
    )

    def action_restore_version(self):
        self.ensure_one()
        document = self.document_id
        if document.file:
            self.env['edm.document.version'].create({'document_id': document.id, 'version_no': document.version_no or 1, 'file': document.file, 'file_name': document.file_name})
        document.write({'file': self.file, 'file_name': self.file_name, 'version_no': (document.version_no or 1) + 1})
        document.message_post(body="Restored version v%s." % (self.version_no or 1))
        return True
