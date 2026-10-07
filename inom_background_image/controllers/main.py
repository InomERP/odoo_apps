from odoo.http import Controller, request, route


class LoginBackground(Controller):

    @route('/dashboard', type='http', auth='public')
    def dashboard(self, **kw):
        company = request.env.company.sudo()
        image = company.login_background

        if not image:
            return request.not_found()

        # Odoo 20: Binary fields return a BinaryValue holding the raw bytes
        # (no longer base64), so serve its content directly.
        return request.make_response(
            image.content,
            [('Content-Type', image.mimetype or 'image/png')]
        )
