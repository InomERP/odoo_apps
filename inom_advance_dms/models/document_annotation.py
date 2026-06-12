from odoo import models, fields, api


class EdmDocumentAnnotation(models.Model):
    _name = "edm.document.annotation"
    _description = "PDF Document Annotation"
    _order = "page_number, create_date"

    document_id = fields.Many2one(
        'edm.document',
        string="Document",
        required=True,
        ondelete='cascade',
        index=True,
    )

    annotation_type = fields.Selection([
        ('highlight', 'Highlight'),
        ('underline', 'Underline'),
        ('strikethrough', 'Strikethrough'),
        ('note', 'Sticky Note'),
        ('text', 'Text Comment'),
        ('drawing', 'Free Drawing'),
        ('rectangle', 'Rectangle'),
        ('square', 'Square'),
        ('ellipse', 'Circle / Ellipse'),
        ('cloud', 'Cloud'),
        ('arrow', 'Arrow'),
        ('signature', 'Signature'),
        ('stamp', 'Stamp'),
        ('line', 'Line'),
        ('darrow', 'Double Arrow'),
    ], string="Type", required=True, default='highlight')

    page_number = fields.Integer(string="Page", default=1)

    # Bounding box (percentage-based, relative to page)
    x = fields.Float(string="X Position", digits=(16, 4))
    y = fields.Float(string="Y Position", digits=(16, 4))
    width = fields.Float(string="Width", digits=(16, 4))
    height = fields.Float(string="Height", digits=(16, 4))

    # Color & style
    color = fields.Char(string="Color", default="#FFFF00")
    opacity = fields.Float(string="Opacity", default=0.5)

    # Content
    content = fields.Text(string="Note / Text")

    # Drawing path for freehand
    path_data = fields.Text(string="SVG Path Data")

    # Author
    user_id = fields.Many2one(
        'res.users',
        string="Author",
        default=lambda self: self.env.user,
        readonly=True,
    )

    is_resolved = fields.Boolean(string="Resolved", default=False)

    # ---------------------------------------------------------
    # ACTIONS
    # ---------------------------------------------------------

    def action_resolve(self):
        self.is_resolved = True

    def action_unresolve(self):
        self.is_resolved = False
