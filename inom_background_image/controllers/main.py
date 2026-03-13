import base64
from odoo.http import request, route, Controller

class LoginBackground(Controller):

    @route('/dashboard', type='http', auth='public')
    def dashboard(self, **kw):
        company = request.env.company

        if not company.login_background:
            return "No Image"

        image = base64.b64decode(company.login_background)

        return request.make_response(
            image,
            [('Content-Type', 'image/png')]
        )