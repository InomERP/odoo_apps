import base64

from odoo import models, fields, api
from odoo.exceptions import UserError
from datetime import timedelta
from markupsafe import Markup


class EdmDocument(models.Model):
    _name = "edm.document"

    def action_open_in_dialog(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'edm.document',
            'res_id': self.id,
            'view_mode': 'form',
            'views': [[False, 'form']],
            'target': 'new',
        }
    _description = "Document"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(required=True, tracking=True)

    annotation_description = fields.Text(string="Annotation Description")

    file = fields.Binary(string="File")
    file_name = fields.Char(string="File Name")

    url = fields.Char(string="URL")

    share_link = fields.Char(string="Share Link")

    document_type = fields.Selection([
        ('file', 'File'),
        ('url', 'URL')
    ], default='file')

    workspace_id = fields.Many2one(
        'edm.workspace',
        string="Workspace"
    )

    folder_id = fields.Many2one(
        'edm.folder',
        string="Folder"
    )

    request_id = fields.Many2one(
        'edm.document.request',
        string="Source Request",
        help="The file request whose uploaded file generated this document."
    )

    owner_id = fields.Many2one(
        'res.users',
        default=lambda self: self.env.user,
        string="Owner"
    )

    tag_ids = fields.Many2many(
        'edm.tag',
        string="Tags"
    )

    state = fields.Selection([
        ('draft', 'Draft'),
        ('waiting', 'Waiting'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ], default='draft', tracking=True)

    version_no = fields.Integer(default=1)

    is_favorite = fields.Boolean(default=False)

    is_trashed = fields.Boolean(default=False)

    trashed_date = fields.Datetime()

    active = fields.Boolean(default=True)

    is_locked = fields.Boolean(default=False)

    expiry_date = fields.Date()

    expiry_status = fields.Selection([
        ('no_expiry', 'No Expiry'),
        ('expiring_soon', 'Expiring Soon'),
        ('expired', 'Expired'),
    ], compute="_compute_expiry_status", store=True)

    file_extension = fields.Char(
        compute="_compute_file_extension",
        store=True
    )

    access_type = fields.Selection([
        ('private', 'Private'),
        ('manager', 'Managers & Owner'),
        ('users', 'Specific Users')
    ], default='private')

    allowed_user_ids = fields.Many2many(
        'res.users',
        string="Allowed Users"
    )

    share_access_level = fields.Selection([
        ('view', 'View only'),
        ('download', 'View & Download'),
        ('annotate', 'View, Download & Annotate'),
    ], string="Share Access Level", default='view',
        help="Level of access granted to users this document is shared with.")

    auto_delete = fields.Boolean()

    can_annotate = fields.Boolean(
        string="Can Annotate",
        compute="_compute_can_annotate",
        help="True if the current user may annotate this document."
    )

    def _compute_can_annotate(self):
        uid = self.env.user.id
        for rec in self:
            can = False
            if rec.owner_id.id == uid:
                # The owner can always annotate their own document.
                can = True
            elif (rec.access_type == 'users'
                  and uid in rec.allowed_user_ids.ids
                  and rec.share_access_level == 'annotate'):
                # Shared users may annotate only when granted that level.
                can = True
            rec.can_annotate = can

    can_download = fields.Boolean(
        string="Can Download",
        compute="_compute_can_download",
        help="True if the current user may download this document."
    )

    def _compute_can_download(self):
        uid = self.env.user.id
        for rec in self:
            can = False
            if rec.owner_id.id == uid:
                can = True
            elif (rec.access_type == 'users'
                  and uid in rec.allowed_user_ids.ids
                  and rec.share_access_level in ('download', 'annotate')):
                can = True
            rec.can_download = can


    # ---------------------------------------------------------
    # COMPUTE
    # ---------------------------------------------------------

    @api.depends('file_name', 'document_type')
    def _compute_file_extension(self):

        for rec in self:

            if rec.document_type == 'url':
                rec.file_extension = 'url'

            elif rec.file_name and '.' in rec.file_name:
                rec.file_extension = rec.file_name.split('.')[-1].lower()

            else:
                rec.file_extension = 'file'

    @api.depends('expiry_date')
    def _compute_expiry_status(self):

        today = fields.Date.today()

        for rec in self:

            if not rec.expiry_date:
                rec.expiry_status = 'no_expiry'

            elif rec.expiry_date < today:
                rec.expiry_status = 'expired'

            elif rec.expiry_date <= today + timedelta(days=7):
                rec.expiry_status = 'expiring_soon'

            else:
                rec.expiry_status = 'no_expiry'

    # ---------------------------------------------------------
    # FAVORITE
    # ---------------------------------------------------------

    def action_toggle_favorite(self):

        for rec in self:
            rec.is_favorite = not rec.is_favorite

    # ---------------------------------------------------------
    # APPROVAL FLOW
    # ---------------------------------------------------------

    def action_submit_approval(self):
        self.state = 'waiting'

    def action_approve_document(self):
        self.state = 'approved'

    def action_reject_document(self):
        self.state = 'rejected'

    def action_reset_to_draft(self):
        self.state = 'draft'

    # ---------------------------------------------------------
    # QUICK ACTIONS
    # ---------------------------------------------------------

    def action_quick_trash(self):

        self.write({
            'is_trashed': True,
            'trashed_date': fields.Datetime.now()
        })

    def action_restore_document(self):

        self.write({
            'is_trashed': False,
            'trashed_date': False
        })

    def action_archive_unarchive_document(self):
        """Toggle the archive (active) state of the selected documents."""
        for document in self:
            document.active = not document.active
        archived = bool(self) and not self[0].active
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': "Archived" if archived else "Restored",
                'message': "Document archived." if archived else "Document restored.",
                'type': 'success',
                'next': {'type': 'ir.actions.client', 'tag': 'reload'},
            },
        }

    def action_lock_document(self):
        """Toggle the lock state of the selected documents."""
        for document in self:
            document.is_locked = not document.is_locked
        locked = bool(self) and self[0].is_locked
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': "Locked" if locked else "Unlocked",
                'message': "Document locked." if locked else "Document unlocked.",
                'type': 'success',
                'next': {'type': 'ir.actions.client', 'tag': 'reload'},
            },
        }

    def action_copy_move_document(self):
        """Duplicate the document and open the new copy."""
        self.ensure_one()
        new_document = self.copy({'name': "%s (Copy)" % (self.name or "Document")})
        return {
            'type': 'ir.actions.act_window',
            'name': "Duplicate / Move Document",
            'res_model': 'edm.document',
            'res_id': new_document.id,
            'view_mode': 'form',
            'views': [(False, 'form')],
            'target': 'current',
        }

    # ---------------------------------------------------------
    # URL OPEN
    # ---------------------------------------------------------

    def action_open_url(self):

        self.ensure_one()

        if not self.url:
            raise UserError("No URL found.")

        return {
            'type': 'ir.actions.act_url',
            'url': self.url,
            'target': 'new',
        }

    # ---------------------------------------------------------
    # PREVIEW
    # ---------------------------------------------------------

    def action_preview_document(self):

        self.ensure_one()

        if self.document_type == 'url' and self.url:
            return {
                'type': 'ir.actions.act_url',
                'url': self.url,
                'target': 'new',
            }

        if not self.file:
            raise UserError("No file uploaded.")

        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%s/%s/file/%s?download=false' % (
                self._name,
                self.id,
                self.file_name or 'file'
            ),
            'target': 'new',
        }

    # ---------------------------------------------------------
    # DOWNLOAD
    # ---------------------------------------------------------

    def action_download_document(self):

        self.ensure_one()

        if not self.file:
            raise UserError("No file found.")

        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%s/%s/file/%s?download=true' % (
                self._name,
                self.id,
                self.file_name or 'file'
            ),
            'target': 'self',
        }

    # ---------------------------------------------------------
    # SHARE
    # ---------------------------------------------------------

    def action_generate_share_link(self):

        self.ensure_one()

        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')

        share_url = f"{base_url}/web#id={self.id}&model=edm.document&view_type=form"

        self.share_link = share_url

        self.message_post(
            body=Markup(
                f'Share link generated: '
                f'<a href="{share_url}" target="_blank">{share_url}</a>'
            )
        )

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Success',
                'message': 'Share link generated successfully',
                'type': 'success',
                'sticky': False,
            }
        }

    # ---------------------------------------------------------
    # CRM / PROJECT / MAIL
    # ---------------------------------------------------------

    def action_create_lead(self):

        if 'crm.lead' not in self.env:
            raise UserError("CRM module is not installed. Please install it to use this feature.")

        lead = self.env['crm.lead'].create({
            'name': self.name,
            'description': 'Lead created from document'
        })

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'crm.lead',
            'res_id': lead.id,
            'view_mode': 'form',
        }

    def action_create_task(self):

        if 'project.task' not in self.env:
            raise UserError("Project module is not installed. Please install it to use this feature.")

        task = self.env['project.task'].create({
            'name': self.name,
            'description': 'Task created from document'
        })

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'project.task',
            'res_id': task.id,
            'view_mode': 'form',
        }

    def action_create_mail(self):

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'mail.compose.message',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_subject': self.name,
                'default_body': 'Document shared from EDM'
            }
        }

    # ---------------------------------------------------------
    # REMINDER / EXPIRY
    # ---------------------------------------------------------

    def action_schedule_reminder(self):

        self.activity_schedule(
            'mail.mail_activity_data_todo',
            summary='Document Reminder',
            note='Reminder for document'
        )

    def action_send_expiry_email(self):

        for rec in self:

            rec.message_post(
                body="Expiry email sent."
            )

            self.env['mail.mail'].create({
                'subject': f'Document Expiry Alert: {rec.name}',
                'body_html': '<p>Document expiry alert.</p>',
                'email_to': rec.owner_id.partner_id.email or self.env.company.email or self.env.user.email,
            }).send()

    # ---------------------------------------------------------
    # ANNOTATION
    # ---------------------------------------------------------

    annotation_ids = fields.One2many(
        'edm.document.annotation',
        'document_id',
        string="Annotations",
    )

    version_ids = fields.One2many(
        'edm.document.version', 'document_id', string='Versions')

    share_token = fields.Char(string="Share Token", copy=False)
    is_public = fields.Boolean(string="Public Share", default=False)
    annotated_file = fields.Binary(string="Annotated File")
    annotated_file_name = fields.Char(string="Annotated File Name")

    annotation_count = fields.Integer(
        compute='_compute_annotation_count',
        string="Annotation Count",
        store=False,
    )

    @api.depends('annotation_ids')
    def _compute_annotation_count(self):
        for rec in self:
            rec.annotation_count = len(rec.annotation_ids)

    def action_open_pdf_annotator(self):
        """Return a client action that opens the JS PDF annotator."""
        self.ensure_one()

        if not self.file or self.file_extension != 'pdf':
            raise UserError("PDF annotation is only available for PDF files.")

        return {
            'type': 'ir.actions.client',
            'tag': 'edm_open_pdf_annotator',
            'context': {
                'document_id': self.id,
                'file_data': self.file if isinstance(self.file, str) else self.file.decode('utf-8'),
                'file_name': self.file_name or 'document.pdf',
            },
        }

    # ---------------------------------------------------------
    # CRON
    # ---------------------------------------------------------


    @api.model
    def cron_check_document_expiry(self):

        docs = self.search([
            ('expiry_status', '=', 'expiring_soon')
        ])

        for doc in docs:

            doc.message_post(
                body="Document expiry alert generated automatically."
            )

            self.env['mail.mail'].create({
                'subject': f'Document Expiry Alert: {doc.name}',
                'body_html': '<p>Your document is expiring soon.</p>',
                'email_to': doc.owner_id.partner_id.email or self.env.company.email or self.env.user.email,
            }).send()

    @api.model
    def cron_auto_delete_trash(self):

        days = int(
            self.env['ir.config_parameter'].sudo().get_param(
                'edm.trash_auto_delete_days',
                default=30
            )
        )

        limit_date = fields.Datetime.now() - timedelta(days=days)

        docs = self.search([
            ('is_trashed', '=', True),
            ('trashed_date', '<=', limit_date)
        ])

        docs.unlink()

    file_color = fields.Char(compute='_compute_file_color', store=False)

    @api.depends('file_extension')
    def _compute_file_color(self):
        color_map = {
            'pdf': '#e74c3c',
            'xls': '#27ae60', 'xlsx': '#27ae60',
            'doc': '#2980b9', 'docx': '#2980b9',
            'png': '#8e44ad', 'jpg': '#8e44ad', 'jpeg': '#8e44ad',
            'zip': '#f39c12',
            'url': '#6f42c1',
        }
        for rec in self:
            rec.file_color = color_map.get(rec.file_extension, '#666666')
