from odoo import models, fields, api


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

    @api.depends('name', 'parent_id', 'parent_id.complete_name')
    def _compute_complete_name(self):
        for folder in self:
            if folder.parent_id:
                folder.complete_name = f"{folder.parent_id.complete_name} / {folder.name}"
            else:
                folder.complete_name = folder.name