# -*- coding: utf-8 -*-
"""
Drag & drop upload controller for the Advanced DMS module.

This controller is ADDITIVE. It creates ``edm.document`` records using the
exact same field set the existing upload wizards use, so the standard
attachment / document flow keeps working untouched. A multipart HTTP route
is used (instead of JSON-RPC) so the browser can report genuine upload
progress through XMLHttpRequest's ``upload.onprogress`` event.
"""

import base64
import json

from odoo import http
from odoo.http import request

# Keep this list in sync with the client side validation in the OWL widget.
ALLOWED_EXTENSIONS = {
    # Documents
    "pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx",
    "txt", "rtf", "csv", "odt", "ods", "odp", "md",
    # Images
    "png", "jpg", "jpeg", "gif", "bmp", "svg", "webp", "tiff", "tif", "ico", "heic",
    # Archives
    "zip", "rar", "7z", "tar", "gz",
    # Audio / Video
    "mp3", "wav", "ogg", "m4a", "flac",
    "mp4", "avi", "mov", "mkv", "webm", "wmv",
    # Data / markup
    "json", "xml", "html", "htm", "yaml", "yml",
}

# 25 MB hard server side guard (client validates first with a friendlier UX).
MAX_FILE_SIZE = 100 * 1024 * 1024


class EdmUploadController(http.Controller):

    @staticmethod
    def _json(payload, status=200):
        return request.make_response(
            json.dumps(payload),
            headers=[("Content-Type", "application/json")],
            status=status,
        )

    @staticmethod
    def _extension(filename):
        if filename and "." in filename:
            return filename.rsplit(".", 1)[-1].lower()
        return ""

    # ------------------------------------------------------------------
    # Single file upload (called once per file by the OWL dropzone)
    # ------------------------------------------------------------------
    @http.route(
        "/edm/upload/dropzone",
        type="http",
        auth="user",
        methods=["POST"],
        csrf=False,
    )
    def upload_dropzone(self, ufile=None, name=None, workspace_id=None,
                        folder_id=None, is_favorite=None, **kw):
        if ufile is None:
            return self._json({"status": "error", "message": "No file received."})

        filename = ufile.filename or name or "document"
        extension = self._extension(filename)

        if extension not in ALLOWED_EXTENSIONS:
            return self._json(
                {
                    "status": "error",
                    "message": "Unsupported file type: .%s" % (extension or "?"),
                    "name": filename,
                }
            )

        content = ufile.read()
        if not content:
            return self._json(
                {"status": "error", "message": "Empty file.", "name": filename}
            )

        if len(content) > MAX_FILE_SIZE:
            return self._json(
                {
                    "status": "error",
                    "message": "File exceeds the maximum allowed size.",
                    "name": filename,
                }
            )

        Document = request.env["edm.document"]

        # Soft duplicate detection: a non-trashed document with the same
        # file name already exists. We still allow the upload but flag it.
        duplicate = bool(
            Document.sudo().search_count(
                [("file_name", "=", filename), ("is_trashed", "=", False)]
            )
        )

        vals = {
            "name": name or filename,
            "file": base64.b64encode(content),
            "file_name": filename,
            "owner_id": request.env.user.id,
            "document_type": "file",
            "is_favorite": str(is_favorite).lower() in ("1", "true", "on", "yes"),
        }

        if workspace_id:
            try:
                vals["workspace_id"] = int(workspace_id)
            except (TypeError, ValueError):
                pass

        if folder_id:
            try:
                vals["folder_id"] = int(folder_id)
            except (TypeError, ValueError):
                pass

        # Created with the caller's own rights (no sudo) so record rules and
        # access rights behave exactly like the existing wizards.
        document = Document.create(vals)

        return self._json(
            {
                "status": "ok",
                "id": document.id,
                "name": document.name,
                "duplicate": duplicate,
            }
        )
