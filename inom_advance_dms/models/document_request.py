from odoo import models, fields, api
from odoo.exceptions import UserError


class EdmDocumentRequest(models.Model):
    _name = 'edm.document.request'
    _description = 'Document Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'request_date desc'

    name = fields.Char(string='Name', required=True, tracking=True)
    requested_by = fields.Many2one('res.users', string='Requested By', default=lambda self: self.env.user, tracking=True)
    requested_to = fields.Many2one('res.users', string='Assigned To', required=True, tracking=True)
    request_date = fields.Datetime(string='Request Date', default=fields.Datetime.now, tracking=True)
    workspace_id = fields.Many2one('edm.workspace', string='Workspace', required=True, tracking=True)

    document_id = fields.Many2one('edm.document', string='Document', tracking=True)
    note = fields.Text(string='Instructions')
    deadline = fields.Date(string='Due Date', tracking=True)

    state = fields.Selection([
        ('requested', 'Pending'),
        ('accepted', 'Approved'),
        ('rejected', 'Declined'),
    ], string='State', default='requested', tracking=True)

    upload_file = fields.Binary(string='Upload File')
    upload_file_name = fields.Char(string='Upload File Name')

    @api.model_create_multi
    def create(self, vals_list):
        # The document is created on approval (Accept), not on creation/upload.
        return super().create(vals_list)

    def write(self, vals):
        res = super().write(vals)
        # A newly uploaded file is only attached and logged here; it does NOT
        # auto-create the document or auto-approve. Approval is explicit.
        if vals.get('upload_file'):
            for rec in self:
                rec.message_post(body="File uploaded. Awaiting review.")
                # If the request was already approved but the uploaded file
                # has not yet become a document, create it now.
                if rec.state == 'accepted' and not rec._document_built_from_upload():
                    rec._create_document_from_uploaded_file()
        return res

    def _create_document_from_uploaded_file(self):
        for rec in self:
            if not rec.upload_file:
                raise UserError("Please upload a file first.")

            document_vals = {
                'name': rec.upload_file_name or rec.name,
                'document_type': 'file',
                'file': rec.upload_file,
                'file_name': rec.upload_file_name or rec.name,
                'workspace_id': rec.workspace_id.id,
                'owner_id': rec.requested_to.id or self.env.user.id,
            }

            # Grant the requester access to the resulting document so they can
            # review/download it (owner is the assignee who provided the file).
            if rec.requested_by:
                document_vals.update({
                    'access_type': 'users',
                    'allowed_user_ids': [(6, 0, [rec.requested_by.id])],
                    'share_access_level': 'download',
                })

            if 'request_id' in self.env['edm.document']._fields:
                document_vals['request_id'] = rec.id

            document = self.env['edm.document'].create(document_vals)

            super(EdmDocumentRequest, rec).write({
                'document_id': document.id,
            })

    def action_accept_request(self):
        for rec in self:
            # On approval, the uploaded file is the actual deliverable, so it
            # always becomes the linked document (any pre-set reference is
            # overwritten). Only skip if a document was already built from it.
            if rec.upload_file and not rec._document_built_from_upload():
                rec._create_document_from_uploaded_file()
            rec.write({'state': 'accepted'})
            rec.message_post(body="Document request approved.")
        return True

    def _document_built_from_upload(self):
        # True only when the linked document was generated from this request's
        # uploaded file (not a manually chosen reference document).
        self.ensure_one()
        if not self.document_id:
            return False
        if 'request_id' in self.env['edm.document']._fields:
            return self.document_id.request_id.id == self.id
        return False

    def action_reject_request(self):
        for rec in self:
            rec.write({'state': 'rejected'})
            rec.message_post(body="Document request declined.")
        return True

    def action_create_document_from_request(self):
        for rec in self:
            if not rec.upload_file:
                raise UserError("Please upload a file first.")
            if not rec._document_built_from_upload():
                rec._create_document_from_uploaded_file()
            rec.write({'state': 'accepted'})
            rec.message_post(body="Document uploaded and request approved.")
        return True

    def action_open_document(self):
        self.ensure_one()
        if not self.document_id:
            raise UserError("No document linked with this request.")
        return {
            'type': 'ir.actions.act_window',
            'name': 'Document',
            'res_model': 'edm.document',
            'res_id': self.document_id.id,
            'view_mode': 'form',
            'target': 'current',
        }