import base64
import logging

from odoo import http
from odoo.exceptions import AccessError
from odoo.http import request

_logger = logging.getLogger(__name__)


class InomLessonContent(http.Controller):
    """Serving a lesson's file.

    Not /web/content: that route reaches any attachment in the database given
    an id. This resolves the lesson first and checks access on it, so the
    record rules that scope a student to their own courses are what decide —
    the same rule that hides an unpublished course from them hides its files.
    """

    @http.route('/ums/lesson/<int:lesson_id>/file', type='http', auth='user',
                sitemap=False)
    def lesson_file(self, lesson_id, **kw):
        lesson = request.env['inom.lesson'].browse(lesson_id).exists()
        if not lesson:
            raise request.not_found()
        try:
            lesson.check_access('read')
        except AccessError:
            _logger.info('INOM lesson: uid %s denied lesson %s',
                         request.env.uid, lesson_id)
            # not_found rather than forbidden: a 403 confirms the lesson
            # exists, which is a fact about somebody else's course.
            raise request.not_found()

        if not lesson.file_data:
            raise request.not_found()

        content = base64.b64decode(lesson.file_data)
        name = lesson.file_name or f'{lesson.name}.pdf'
        is_pdf = name.lower().endswith('.pdf')

        return request.make_response(content, headers=[
            # inline for a PDF so the browser shows it in the page rather than
            # downloading it — the point is reading it here.
            ('Content-Type', 'application/pdf' if is_pdf
             else 'application/octet-stream'),
            ('Content-Length', len(content)),
            ('Content-Disposition',
             f'{"inline" if is_pdf else "attachment"}; filename="{name}"'),
            ('Cache-Control', 'private, max-age=600'),
        ])
