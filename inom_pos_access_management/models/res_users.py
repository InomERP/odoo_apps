# -*- coding: utf-8 -*-
from odoo import models, fields


class ResUsers(models.Model):
    """Add 'POS Management Permission' to res.users.

    Why @property (not __init__)
    -----------------------------
    Every model instance in Odoo 15+ is constructed via
    ``__init__(self, env, ids, prefetch_ids)``. Overriding ``__init__``
    with the older ``(self, pool, cr)`` signature breaks every
    ``env['res.users']`` call across the whole registry and produces:

        TypeError: ResUsers.__init__() takes 3 positional arguments
                   but 4 were given

    The portable, version-safe way to extend ``SELF_READABLE_FIELDS`` /
    ``SELF_WRITEABLE_FIELDS`` is the ``@property`` form below. It works
    on BOTH:

      * Odoo 17, where the base ``res.users`` declares these as plain
        class attributes — ``super().SELF_*_FIELDS`` then yields the
        list directly via normal attribute lookup;

      * Odoo 18+, where the base declared them as ``@property`` —
        ``super().SELF_*_FIELDS`` calls the parent property and yields
        the list.

    In both cases the Odoo runtime reads these via
    ``self.SELF_*_FIELDS`` (instance access), which triggers Python's
    descriptor protocol and the property is correctly invoked.
    """
    _inherit = 'res.users'

    pos_management_permission = fields.Boolean(
        string='POS Management Permission',
        help="Enable to allow this user to manage POS access rights. "
             "When enabled, the user can be assigned access rules from "
             "Point of Sale > Configuration > POS Access Rights.",
    )
    pos_access_rights_ids = fields.One2many(
        'pos.access.rights',
        'user_id',
        string='POS Access Rights',
    )

    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS + [
            'pos_management_permission',
        ]

    @property
    def SELF_WRITEABLE_FIELDS(self):
        return super().SELF_WRITEABLE_FIELDS + [
            'pos_management_permission',
        ]