from odoo import http
from odoo.http import request
from werkzeug.exceptions import NotFound, Forbidden
from markupsafe import Markup
import base64


class DocumentPortalController(http.Controller):

    @http.route(['/my/documents'], type='http', auth='user', website=True)
    def portal_my_documents(self, **kw):
        user = request.env.user
        documents = request.env['edm.document'].sudo().search([
            ('is_trashed', '=', False),
            '|',
                ('owner_id', '=', user.id),
                ('allowed_user_ids', 'in', user.id),
        ])

        return request.render(
            'inom_advance_dms.portal_my_documents',
            {'documents': documents, 'user': user}
        )

    def _portal_access_doc(self, document_id):
        """Return the document only if the current user owns it or it is
        shared with them; otherwise raise NotFound. Prevents direct-id access."""
        user = request.env.user
        document = request.env['edm.document'].sudo().browse(document_id)
        if not document.exists() or document.is_trashed:
            raise NotFound()
        if document.owner_id.id != user.id and user.id not in document.allowed_user_ids.ids:
            raise NotFound()
        return document

    @http.route(['/my/document/view/<int:document_id>'], type='http', auth='user', website=True)
    def portal_view_document(self, document_id, **kw):
        document = self._portal_access_doc(document_id)
        if not document.file:
            raise NotFound()
        filecontent = base64.b64decode(document.annotated_file or document.file)
        filename = document.annotated_file_name or document.file_name or document.name or 'document'
        ext = (document.file_extension or '').lower()
        mimetype = 'application/pdf' if ext == 'pdf' else 'application/octet-stream'
        return request.make_response(
            filecontent,
            headers=[
                ('Content-Type', mimetype),
                ('Content-Disposition', 'inline; filename="%s"' % filename),
            ]
        )

    @http.route(['/my/document/download/<int:document_id>'], type='http', auth='user', website=True)
    def portal_download_document(self, document_id, **kw):
        user = request.env.user
        document = self._portal_access_doc(document_id)

        # View-only share: shared users may NOT download (owner always can).
        if document.owner_id.id != user.id and document.share_access_level == 'view':
            raise Forbidden()

        if not document.file:
            raise NotFound()

        filecontent = base64.b64decode(document.annotated_file or document.file)
        filename = document.annotated_file_name or document.file_name or document.name or 'document'

        return request.make_response(
            filecontent,
            headers=[
                ('Content-Type', 'application/octet-stream'),
                ('Content-Disposition', 'attachment; filename="%s"' % filename),
            ]
        )

    @http.route(['/my/upload-requests'], type='http', auth='user', website=True)
    def portal_upload_requests(self, **kw):
        upload_requests = request.env['edm.document.request'].sudo().search([
            '|',
            ('requested_to', '=', request.env.user.id),
            ('requested_by', '=', request.env.user.id),
        ])

        return request.render(
            'inom_advance_dms.portal_upload_requests',
            {'upload_requests': upload_requests}
        )

    @http.route(['/my/upload-request/<int:req_id>/accept'], type='http', auth='user', website=True)
    def portal_upload_request_accept(self, req_id, **kw):
        upload_request = request.env['edm.document.request'].sudo().browse(req_id)

        if not upload_request.exists():
            raise NotFound()

        upload_request.action_accept_request()
        return request.redirect('/my/upload-requests')

    @http.route(['/my/upload-request/<int:req_id>/refuse'], type='http', auth='user', website=True)
    def portal_upload_request_refuse(self, req_id, **kw):
        upload_request = request.env['edm.document.request'].sudo().browse(req_id)

        if not upload_request.exists():
            raise NotFound()

        upload_request.action_reject_request()
        return request.redirect('/my/upload-requests')

    @http.route(['/documents/share/<string:token>'], type='http', auth='public', website=True)
    def shared_document(self, token=None, **kwargs):
        document = request.env['edm.document'].sudo().search([
            ('share_token', '=', token),
            ('is_public', '=', True),
            ('is_trashed', '=', False),
        ], limit=1)

        if not document:
            raise NotFound()

        download_url = '/documents/share/%s/download' % token

        html = """
        <html>
            <head>
                <title>Shared Document</title>
                <style>
                    body {font-family: Arial; margin: 40px; background: #f5f5f5;}
                    .card {border: 1px solid #ddd; padding: 25px; border-radius: 10px; max-width: 700px; background: white; margin: auto;}
                    .btn {background: #714B67; color: white; padding: 10px 18px; text-decoration: none; border-radius: 5px; display: inline-block;}
                    p {font-size: 15px;}
                </style>
            </head>
            <body>
                <div class="card">
                    <h2>%s</h2>
                    <hr/>
                    <p><b>Workspace:</b> %s</p>
                    <p><b>Folder:</b> %s</p>
                    <p><b>Owner:</b> %s</p>
                    <br/>
                    <a class="btn" href="%s">Download</a>
                </div>
            </body>
        </html>
        """ % (
            document.name or '',
            document.workspace_id.name or '-',
            document.folder_id.name or '-',
            document.owner_id.name or '-',
            download_url,
        )

        return request.make_response(
            Markup(html),
            headers=[('Content-Type', 'text/html')]
        )

    @http.route(['/documents/share/<string:token>/download'], type='http', auth='public', website=True)
    def shared_document_download(self, token=None, **kwargs):
        document = request.env['edm.document'].sudo().search([
            ('share_token', '=', token),
            ('is_public', '=', True),
            ('is_trashed', '=', False),
        ], limit=1)

        if not document or not document.file:
            raise NotFound()

        filecontent = base64.b64decode(document.annotated_file or document.file)
        filename = document.annotated_file_name or document.file_name or document.name or 'document'

        return request.make_response(
            filecontent,
            headers=[
                ('Content-Type', 'application/octet-stream'),
                ('Content-Disposition', 'attachment; filename="%s"' % filename),
            ]
        )