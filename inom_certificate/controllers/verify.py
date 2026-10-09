import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class InomVerify(http.Controller):
    """Public certificate verification.

    Deliberately unauthenticated: the person checking is an employer or a
    university admissions office, and requiring an account guarantees nobody
    ever uses it — which makes the verification code decorative.

    Three rules keep an open endpoint from becoming a data source:

    * it answers only on an exact code, never a name or an enrolment number,
      so it cannot be searched;
    * it returns type, name and issue date and nothing else;
    * it never distinguishes "no such code" from "code exists but the
      certificate was withdrawn" — both are simply not found.
    """

    @http.route('/verify/<string:code>', type='http', auth='public',
                website=False, sitemap=False)
    def verify(self, code, **kw):
        values = {'found': False}

        # sudo() because the caller is the public user by design. The lookup is
        # constrained to an exact issued code, which is what keeps this from
        # being a way to read the certificate register.
        record = request.env['inom.certificate.request'].sudo().search([
            ('verification_code', '=', code),
            ('state', '=', 'issued'),
        ], limit=1)

        if record:
            values = {
                'found': True,
                'certificate_type': record.type_id.name,
                'student_name': record.student_id.name,
                'issued_on': record.issued_on,
                'institution': record.company_id.name,
            }
        else:
            _logger.info('INOM verify: no match for code %s', code[:4] + '…')

        return request.render('inom_certificate.verify_page', values)
