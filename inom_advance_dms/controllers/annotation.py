import json
import uuid

from odoo import http
from odoo.http import request


class DocumentAnnotationController(http.Controller):

    # ----------------------------------------------------------
    # LOAD annotations for a document
    # ----------------------------------------------------------
    @http.route(
        '/edm/annotation/load/<int:document_id>',
        type='http',
        auth='user',
        methods=['GET'],
        csrf=False,
    )
    def annotation_load(self, document_id, **kw):
        document = request.env['edm.document'].sudo().browse(document_id)
        annotations = request.env['edm.document.annotation'].sudo().search([
            ('document_id', '=', document_id),
        ])

        data = []
        for ann in annotations:
            data.append({
                'id': ann.id,
                'annotation_type': ann.annotation_type,
                'page_number': ann.page_number,
                'x': ann.x,
                'y': ann.y,
                'width': ann.width,
                'height': ann.height,
                'color': ann.color,
                'opacity': ann.opacity,
                'content': ann.content or '',
                'path_data': ann.path_data or '',
                'user_id': ann.user_id.id,
                'user_name': ann.user_id.name,
                'is_resolved': ann.is_resolved,
            })

        return request.make_response(
            json.dumps({'status': 'ok', 'annotations': data, 'description': document.annotation_description or ''}),
            headers=[('Content-Type', 'application/json')]
        )

    # ----------------------------------------------------------
    # SAVE annotation description (free-text note on the document)
    # ----------------------------------------------------------
    @http.route(
        '/edm/annotation/description',
        type='json',
        auth='user',
        methods=['POST'],
        csrf=False,
    )
    def annotation_description(self, document_id=None, description=None, **kw):
        if not document_id:
            return {'status': 'error', 'message': 'No document id'}
        document = request.env['edm.document'].sudo().browse(int(document_id))
        if not document.exists():
            return {'status': 'error', 'message': 'Document not found'}
        document.annotation_description = description or ''
        return {'status': 'ok'}

    # ----------------------------------------------------------
    # SHARE annotated PDF (generates public share link)
    # ----------------------------------------------------------
    @http.route(
        '/edm/annotation/share',
        type='http',
        auth='user',
        methods=['POST'],
        csrf=False,
    )
    def annotation_share(self, document_id=None, pdf_data=None, **kw):
        if not document_id or not pdf_data:
            return request.make_response(
                json.dumps({'status': 'error', 'message': 'Missing data'}),
                headers=[('Content-Type', 'application/json')]
            )
        document = request.env['edm.document'].sudo().browse(int(document_id))
        if not document.exists():
            return request.make_response(
                json.dumps({'status': 'error', 'message': 'Document not found'}),
                headers=[('Content-Type', 'application/json')]
            )
        if ',' in pdf_data and pdf_data.strip().startswith('data:'):
            pdf_data = pdf_data.split(',', 1)[1]
        token = document.share_token or uuid.uuid4().hex
        document.sudo().write({
            'annotated_file': pdf_data,
            'annotated_file_name': (document.name or 'document') + '_annotated.pdf',
            'is_public': True,
            'share_token': token,
        })
        base = request.httprequest.host_url.rstrip('/')
        return request.make_response(
            json.dumps({'status': 'ok', 'url': base + '/documents/share/' + token}),
            headers=[('Content-Type', 'application/json')]
        )

    # ----------------------------------------------------------
    # SAVE VERSION of annotated PDF
    # ----------------------------------------------------------
    @http.route(
        '/edm/annotation/save_version',
        type='http',
        auth='user',
        methods=['POST'],
        csrf=False,
    )
    def annotation_save_version(self, document_id=None, pdf_data=None, file_name=None, **kw):
        if not document_id or not pdf_data:
            return request.make_response(
                json.dumps({'status': 'error', 'message': 'Missing data'}),
                headers=[('Content-Type', 'application/json')]
            )
        document = request.env['edm.document'].sudo().browse(int(document_id))
        if not document.exists():
            return request.make_response(
                json.dumps({'status': 'error', 'message': 'Document not found'}),
                headers=[('Content-Type', 'application/json')]
            )
        if ',' in pdf_data and pdf_data.strip().startswith('data:'):
            pdf_data = pdf_data.split(',', 1)[1]
        Version = request.env['edm.document.version'].sudo()
        existing = Version.search([('document_id', '=', document.id)])
        nums = existing.mapped('version_no') or [document.version_no or 0]
        next_no = (max(nums) or 0) + 1
        Version.create({
            'document_id': document.id,
            'version_no': next_no,
            'file': pdf_data,
            'file_name': file_name or ('annotated_v%s.pdf' % next_no),
        })
        document.sudo().write({'version_no': next_no})
        return request.make_response(
            json.dumps({'status': 'ok', 'version_no': next_no}),
            headers=[('Content-Type', 'application/json')]
        )

    # ----------------------------------------------------------
    # SAVE (create/update) a single annotation
    # ----------------------------------------------------------
    @http.route(
        '/edm/annotation/save',
        type='json',
        auth='user',
        methods=['POST'],
        csrf=False,
    )
    def annotation_save(self, **post):
        ann_id = post.get('id')
        document_id = post.get('document_id')

        vals = {
            'annotation_type': post.get('annotation_type', 'highlight'),
            'page_number': int(post.get('page_number', 1)),
            'x': float(post.get('x', 0)),
            'y': float(post.get('y', 0)),
            'width': float(post.get('width', 0)),
            'height': float(post.get('height', 0)),
            'color': post.get('color', '#FFFF00'),
            'opacity': float(post.get('opacity', 0.5)),
            'content': post.get('content', ''),
            'path_data': post.get('path_data', ''),
        }

        if ann_id:
            ann = request.env['edm.document.annotation'].sudo().browse(int(ann_id))
            if ann.exists():
                ann.write(vals)
                return {'status': 'ok', 'id': ann.id}
        else:
            vals['document_id'] = int(document_id)
            ann = request.env['edm.document.annotation'].sudo().create(vals)
            return {'status': 'ok', 'id': ann.id}

        return {'status': 'error', 'message': 'Annotation not found'}

    # ----------------------------------------------------------
    # DELETE an annotation
    # ----------------------------------------------------------
    @http.route(
        '/edm/annotation/delete',
        type='json',
        auth='user',
        methods=['POST'],
        csrf=False,
    )
    def annotation_delete(self, **post):
        ann_id = post.get('id')
        if ann_id:
            ann = request.env['edm.document.annotation'].sudo().browse(int(ann_id))
            if ann.exists():
                ann.unlink()
                return {'status': 'ok'}
        return {'status': 'error', 'message': 'Annotation not found'}

    # ----------------------------------------------------------
    # RESOLVE / UNRESOLVE
    # ----------------------------------------------------------
    @http.route(
        '/edm/annotation/resolve',
        type='json',
        auth='user',
        methods=['POST'],
        csrf=False,
    )
    def annotation_resolve(self, **post):
        ann_id = post.get('id')
        resolved = post.get('resolved', True)
        if ann_id:
            ann = request.env['edm.document.annotation'].sudo().browse(int(ann_id))
            if ann.exists():
                ann.is_resolved = resolved
                return {'status': 'ok'}
        return {'status': 'error', 'message': 'Annotation not found'}
