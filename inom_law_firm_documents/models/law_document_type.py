# -*- coding: utf-8 -*-
from odoo import fields, models


class LawDocumentType(models.Model):
    _name = "law.document.type"
    _description = "Document Type"
    _order = "name"

    name = fields.Char(required=True, translate=True)
    code = fields.Char()
    active = fields.Boolean(default=True)
