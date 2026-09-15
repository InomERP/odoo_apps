from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class EdmFolder(models.Model):
    _name = 'edm.folder'
    _description = 'Document Folder'
    _parent_name = 'parent_id'
    _rec_name = 'name'

    name = fields.Char(string='Folder Name', required=True)
    parent_id = fields.Many2one('edm.folder', string='Parent Folder', ondelete='cascade')
    child_ids = fields.One2many('edm.folder', 'parent_id', string='Sub Folders')
    workspace_id = fields.Many2one('edm.workspace', string='Workspace')

    complete_name = fields.Char(
        string='Complete Name',
        compute='_compute_complete_name',
        store=True,
        recursive=True,
    )

    @api.constrains('parent_id')
    def _check_folder_recursion(self):
        """Refuse a folder loop.

        Without this a folder can end up as its own ancestor. Odoo's search
        panel then walks the parent chain forever, which hangs the request
        thread and leaves the document views stuck on "Loading" - with no
        error anywhere, because nothing actually fails.
        """
        if not self._check_recursion():
            raise ValidationError(_(
                "A folder cannot be placed inside itself or inside one of "
                "its own sub-folders."))

    @api.depends('name', 'parent_id', 'parent_id.complete_name')
    def _compute_complete_name(self):
        for folder in self:
            if folder.parent_id:
                folder.complete_name = f"{folder.parent_id.complete_name} / {folder.name}"
            else:
                folder.complete_name = folder.name