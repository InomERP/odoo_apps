# -*- coding: utf-8 -*-
from odoo import api, fields, models


class UnivLmsMaterial(models.Model):
    _name = "univ.lms.material"
    _description = "Study Material"
    _inherit = ["mail.thread"]
    _order = "subject_id, sequence, version desc"

    name = fields.Char(string="Title", required=True, tracking=True)
    sequence = fields.Integer(default=10)
    subject_id = fields.Many2one(comodel_name="univ.subject", string="Subject",
                                 required=True, index=True)
    faculty_id = fields.Many2one(comodel_name="univ.faculty", string="Faculty")
    material_type = fields.Selection(
        selection=[("note", "Study Note"), ("video", "Video Resource"),
                   ("doc", "Document"), ("link", "External Link"),
                   ("class", "Online Class")],
        string="Type", default="note", required=True)
    version = fields.Integer(string="Version", default=1)
    description = fields.Text(string="Description")
    attachment_ids = fields.Many2many(comodel_name="ir.attachment",
                                      string="Files")
    url = fields.Char(string="Resource URL")
    online_class_url = fields.Char(string="Online Class Link",
                                   help="Zoom / Google Meet / Microsoft Teams link.")
    class_datetime = fields.Datetime(string="Class Time")
    state = fields.Selection(
        selection=[("draft", "Draft"), ("published", "Published"),
                   ("archived", "Archived")],
        string="Status", default="draft", required=True, tracking=True)
    company_id = fields.Many2one(
        comodel_name="res.company", string="Company",
        default=lambda self: self.env.company, index=True)

    def action_publish(self):
        self.write({"state": "published"})

    def action_archive_material(self):
        self.write({"state": "archived"})

    def action_new_version(self):
        """Supersede with an incremented version, archiving the current one."""
        self.ensure_one()
        new = self.copy({
            "version": self.version + 1,
            "state": "draft",
        })
        self.action_archive_material()
        return {
            "type": "ir.actions.act_window",
            "res_model": "univ.lms.material",
            "res_id": new.id,
            "view_mode": "form",
            "target": "current",
        }
