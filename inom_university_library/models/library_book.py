# -*- coding: utf-8 -*-
from odoo import api, fields, models


class UnivLibraryBook(models.Model):
    _name = "univ.library.book"
    _description = "Library Book"
    _inherit = ["mail.thread"]
    _order = "name"

    name = fields.Char(string="Title", required=True, tracking=True)
    isbn = fields.Char(string="ISBN", tracking=True)
    category_id = fields.Many2one(comodel_name="univ.library.category",
                                  string="Category", index=True)
    author_ids = fields.Many2many(comodel_name="univ.library.author",
                                  string="Authors")
    publisher_id = fields.Many2one(comodel_name="univ.library.publisher",
                                   string="Publisher")
    edition = fields.Char(string="Edition")
    publish_year = fields.Char(string="Year")
    shelf = fields.Char(string="Shelf / Location")
    description = fields.Text(string="Description")
    image = fields.Image(string="Cover")
    copy_ids = fields.One2many(comodel_name="univ.library.copy",
                               inverse_name="book_id", string="Copies")
    copies_count = fields.Integer(string="Total Copies",
                                  compute="_compute_counts", store=True)
    available_count = fields.Integer(string="Available",
                                     compute="_compute_counts", store=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        comodel_name="res.company", string="Company",
        default=lambda self: self.env.company, index=True)

    _sql_constraints = [
        ("isbn_uniq", "unique(isbn, company_id)",
         "ISBN must be unique per company."),
    ]

    @api.depends("copy_ids", "copy_ids.state")
    def _compute_counts(self):
        for book in self:
            book.copies_count = len(book.copy_ids)
            book.available_count = len(
                book.copy_ids.filtered(lambda c: c.state == "available"))

    def action_view_copies(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Copies"),
            "res_model": "univ.library.copy",
            "view_mode": "list,form",
            "domain": [("book_id", "=", self.id)],
            "context": {"default_book_id": self.id},
        }


class UnivLibraryCopy(models.Model):
    _name = "univ.library.copy"
    _description = "Book Copy"
    _order = "book_id, barcode"

    name = fields.Char(string="Copy", compute="_compute_name", store=True)
    book_id = fields.Many2one(comodel_name="univ.library.book", string="Book",
                              required=True, ondelete="cascade", index=True)
    barcode = fields.Char(string="Barcode / Accession No.", required=True,
                          copy=False, index=True)
    state = fields.Selection(
        selection=[
            ("available", "Available"),
            ("issued", "Issued"),
            ("reserved", "Reserved"),
            ("lost", "Lost"),
            ("damaged", "Damaged"),
        ], string="Status", default="available", required=True, index=True)
    company_id = fields.Many2one(
        comodel_name="res.company", string="Company",
        related="book_id.company_id", store=True, index=True)

    _sql_constraints = [
        ("barcode_uniq", "unique(barcode, company_id)",
         "Each copy barcode must be unique."),
    ]

    @api.depends("book_id", "barcode")
    def _compute_name(self):
        for copy in self:
            copy.name = "%s [%s]" % (copy.book_id.name or "", copy.barcode or "")
