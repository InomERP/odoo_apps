from odoo import models, fields, api


class DocumentShareWizard(models.TransientModel):
    _name = 'edm.document.share.wizard'
    _description = 'Document Share Wizard'

    document_id = fields.Many2one('edm.document', string='Document')
    user_ids = fields.Many2many('res.users', string='Users')
    access_level = fields.Selection([
        ('view', 'View only'),
        ('download', 'View & Download'),
        ('annotate', 'View, Download & Annotate'),
    ], string='Access', default='view', required=True,
        help="What shared users are allowed to do with this document.")
    is_pdf = fields.Boolean(
        string='Is PDF',
        compute='_compute_is_pdf',
    )
    note = fields.Text(string='Note')

    @api.depends('document_id')
    def _compute_is_pdf(self):
        for wizard in self:
            doc = wizard.document_id
            wizard.is_pdf = bool(
                doc and (doc.file_extension or '').lower() == 'pdf'
            )

    def action_share(self):
        for wizard in self:
            document = wizard.document_id
            if not document:
                continue

            # Grant explicit access to the selected users.
            if wizard.user_ids:
                document.write({
                    'access_type': 'users',
                    'allowed_user_ids': [(4, user.id) for user in wizard.user_ids],
                    'share_access_level': wizard.access_level,
                })

            level_label = dict(
                self._fields['access_level'].selection
            ).get(wizard.access_level, wizard.access_level)
            users = ", ".join(wizard.user_ids.mapped('name')) or "no users"
            body = "Document shared with: %s (access: %s)" % (users, level_label)
            if wizard.note:
                body += "<br/>%s" % wizard.note
            document.message_post(body=body)

        return {'type': 'ir.actions.act_window_close'}
