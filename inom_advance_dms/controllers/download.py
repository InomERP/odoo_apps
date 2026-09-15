# -*- coding: utf-8 -*-
"""Bulk download controller.

The archive is built into an anonymous temporary file and streamed back to
the browser. Documents are decoded one at a time and the record cache is
dropped after each of them, so downloading a large selection never holds
every payload - nor the finished archive - in memory.

``tempfile.TemporaryFile`` has no name on disk, so the data lives only as
long as the file handle: nothing can be left behind, even if the response is
interrupted or the worker is recycled.
"""

import tempfile

from werkzeug.wsgi import wrap_file

from odoo import http
from odoo.http import request, Response, content_disposition
from odoo.exceptions import AccessError


class EdmDownloadController(http.Controller):

    @http.route('/edm/documents/download_zip', type='http', auth='user')
    def download_zip(self, ids=None, filename=None, **kwargs):
        document_ids = []
        for raw_id in (ids or '').split(','):
            raw_id = raw_id.strip()
            if raw_id.isdigit():
                document_ids.append(int(raw_id))

        if not document_ids:
            return request.not_found()

        Document = request.env['edm.document']
        documents = Document.browse(document_ids).exists()
        try:
            # Standard access rights / record rules; no sudo anywhere.
            # Odoo 18 merged the two checks into check_access(); Odoo 17 keeps
            # check_access_rights() and check_access_rule() separate.
            if hasattr(documents, 'check_access'):
                documents.check_access('read')
            else:
                documents.check_access_rights('read')
                documents.check_access_rule('read')
        except AccessError:
            return request.make_response(
                "You are not allowed to download some of these documents.",
                headers=[('Content-Type', 'text/plain')],
                status=403,
            )

        documents = documents.filtered(lambda doc: doc.document_type != 'url')
        if not documents:
            return request.not_found()

        archive = tempfile.TemporaryFile()
        try:
            default_name = documents._write_zip(archive)
            size = archive.tell()
            archive.seek(0)
        except Exception:
            archive.close()
            raise

        response = Response(
            wrap_file(request.httprequest.environ, archive),
            direct_passthrough=True,
            headers=[
                ('Content-Type', 'application/zip'),
                ('Content-Length', str(size)),
                ('Content-Disposition',
                 content_disposition(filename or default_name)),
                # A freshly built archive is never reusable from a cache.
                ('Cache-Control', 'no-store'),
                ('X-Content-Type-Options', 'nosniff'),
            ],
        )
        response.call_on_close(archive.close)
        return response
