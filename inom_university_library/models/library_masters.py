# -*- coding: utf-8 -*-
from odoo import fields, models


class UnivLibraryCategory(models.Model):
    _name = "univ.library.category"
    _description = "Library Category"
    _order = "name"

    name = fields.Char(string="Category", required=True)
    code = fields.Char(string="Code")
    parent_id = fields.Many2one(comodel_name="univ.library.category",
                                string="Parent")
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        comodel_name="res.company", string="Company",
        default=lambda self: self.env.company, index=True)


class UnivLibraryAuthor(models.Model):
    _name = "univ.library.author"
    _description = "Author"
    _order = "name"

    name = fields.Char(string="Author", required=True)
    bio = fields.Text(string="Biography")
    active = fields.Boolean(default=True)


class UnivLibraryPublisher(models.Model):
    _name = "univ.library.publisher"
    _description = "Publisher"
    _order = "name"

    name = fields.Char(string="Publisher", required=True)
    city = fields.Char(string="City")
    active = fields.Boolean(default=True)
