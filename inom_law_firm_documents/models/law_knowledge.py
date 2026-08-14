# -*- coding: utf-8 -*-
from odoo import api, fields, models


class LawAct(models.Model):
    _name = "law.act"
    _description = "Act / Statute"
    _order = "name"

    name = fields.Char(string="Act Name", required=True, translate=True)
    year = fields.Char()
    jurisdiction = fields.Char()
    description = fields.Text()
    section_ids = fields.One2many("law.section", "act_id", string="Sections")
    active = fields.Boolean(default=True)


class LawSection(models.Model):
    _name = "law.section"
    _description = "Act Section"
    _order = "act_id, sequence, id"

    act_id = fields.Many2one("law.act", string="Act", required=True, ondelete="cascade")
    sequence = fields.Integer(default=10)
    number = fields.Char(string="Section No.")
    title = fields.Char(required=True)
    text = fields.Text()
    active = fields.Boolean(default=True)

    @api.depends("act_id.name", "number", "title")
    def _compute_display_name(self):
        for section in self:
            act = section.act_id.name or ''
            title = section.title or ''
            label = "S.%s %s" % (section.number, title) if section.number else title
            section.display_name = "%s — %s" % (act, label) if act else label


class LawCaseLaw(models.Model):
    _name = "law.case.law"
    _description = "Case Law / Precedent"
    _order = "name"

    name = fields.Char(string="Citation / Title", required=True, translate=True)
    citation = fields.Char()
    court = fields.Char()
    year = fields.Char()
    summary = fields.Text()
    judgment_text = fields.Text()
    active = fields.Boolean(default=True)


class LawKnowledgeNote(models.Model):
    _name = "law.knowledge.note"
    _description = "Legal Knowledge Note"
    _inherit = ["mail.thread"]
    _order = "name"

    name = fields.Char(string="Title", required=True)
    content = fields.Html()
    author_id = fields.Many2one("res.users", default=lambda self: self.env.user)
    active = fields.Boolean(default=True)
