from odoo import api, models
from odoo.fields import Domain


class BaseReadonlyAccess(models.AbstractModel):
    """Odoo 20 equivalent of the former ir.model.access/ir.rule hooks.

    The Odoo 19 module blocked every write/create/unlink operation for users in
    the Readonly Access group.  Odoo 20 merged ACLs and record rules into
    ``ir.access`` and removed ``check_access_rights``; every access check
    (``check_access``, ``has_access``, ``_filtered_access``) now goes through
    ``_access_domain``, so the restriction is applied there.  Superuser/sudo
    calls never reach this method, so internal ``sudo()`` writes keep working.
    """

    _inherit = "base"

    @api.model
    def _access_domain(self, operation):
        domain = super()._access_domain(operation)
        if operation != "read" and self.env.user.has_group(
            "inom_readonly_user.group_users_readonly"
        ):
            return Domain.FALSE
        return domain
