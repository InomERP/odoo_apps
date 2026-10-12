# -*- coding: utf-8 -*-
from odoo import _
from odoo.exceptions import UserError
from odoo.http import request

from odoo.addons.auth_signup.controllers.main import AuthSignupHome


class UnivAuthSignupHome(AuthSignupHome):
    """Req 2: make 'Parent / Student' a mandatory choice at registration and
    persist it on the new portal user's contact record."""

    VALID_ACCOUNT_TYPES = ("student", "parent")

    def do_signup(self, qcontext):
        # Enforce the choice ONLY when the field is actually present on the
        # submitted form. This prevents a hard lock-out if, for any reason,
        # the dropdown is not rendered (e.g. before the view upgrade lands).
        if "account_type" in request.params:
            account_type = request.params.get("account_type")
            if account_type not in self.VALID_ACCOUNT_TYPES:
                raise UserError(_(
                    "Please select whether you are registering as a "
                    "Student or a Parent."
                ))
        return super().do_signup(qcontext)

    def web_auth_signup(self, *args, **kw):
        response = super().web_auth_signup(*args, **kw)
        # On a successful signup the new user is authenticated in this request;
        # store the chosen type on their contact.
        account_type = request.params.get("account_type")
        user = request.env.user
        if (
            account_type in self.VALID_ACCOUNT_TYPES
            and user
            and not user._is_public()
            and user.partner_id
            and not user.partner_id.univ_account_type
        ):
            user.partner_id.sudo().write({"univ_account_type": account_type})
        return response
