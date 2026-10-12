# -*- coding: utf-8 -*-
# Part of InomERP. See LICENSE file for full copyright and licensing details.
# Copyright (C) InomERP Pvt Ltd (<https://inomerp.in>).
from odoo import api, fields, models


class UnivDocumentPreview(models.TransientModel):
    """In-Odoo document preview.

    Renders the uploaded applicant document inside a modal dialog using an
    embedded viewer (browser PDF viewer for PDFs, inline image for images) so
    the reviewer never leaves the page, no download is forced and no external
    application is launched. Storage, upload and access rights are untouched.
    """

    _name = "univ.document.preview"
    _description = "Document Preview"

    document_id = fields.Many2one(
        comodel_name="univ.applicant.document",
        string="Document",
        required=True,
        ondelete="cascade",
    )
    file_name = fields.Char(related="document_id.file_name", readonly=True)
    preview_html = fields.Html(
        string="Preview",
        compute="_compute_preview_html",
        sanitize=False,
    )

    @api.depends("document_id")
    def _compute_preview_html(self):
        for wizard in self:
            document = wizard.document_id
            if not document or not document.file:
                wizard.preview_html = (
                    "<div class='alert alert-warning mb-0'>"
                    "No file uploaded to preview.</div>"
                )
                continue
            # Inline content URL (no forced download). The viewer is embedded
            # in this modal, so the user stays on the same page.
            url = (
                "/web/content/univ.applicant.document/%s/file"
                "?download=false&filename=%s"
                % (document.id, document.file_name or "document")
            )
            name = (document.file_name or "").lower()
            is_image = name.endswith(
                (".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp")
            )
            if is_image:
                wizard.preview_html = (
                    "<div class='text-center' style='max-height:75vh;"
                    "overflow:auto;'>"
                    "<img src='%s' style='max-width:100%%;height:auto;'/>"
                    "</div>" % url
                )
            else:
                # PDF (and any other browser-renderable type)
                wizard.preview_html = (
                    "<iframe src='%s' "
                    "style='width:100%%;height:75vh;border:0;'></iframe>" % url
                )
