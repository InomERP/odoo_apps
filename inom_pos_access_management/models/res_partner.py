# -*- coding: utf-8 -*-
from odoo import models


class ResPartner(models.Model):
    """Stub kept to preserve the module's file layout.

    Odoo 17 vs Odoo 18
    ------------------
    The Odoo-18 module overrode ``_load_pos_data_domain`` directly on
    ``res.partner`` to filter customers shipped to the POS. That hook
    does not exist in Odoo 17. The equivalent (and arguably cleaner)
    Odoo-17 restriction is implemented on ``pos.session`` via
    ``_loader_params_res_partner`` — see ``models/pos_session.py``.

    That single hook automatically covers both the initial customer
    load AND every on-demand partner-search RPC (because
    ``get_pos_ui_res_partner_by_params`` re-uses
    ``_loader_params_res_partner`` to build its base query).

    This file is intentionally left as a no-op subclass so the
    ``models/__init__.py`` import order, and any external Python
    references to this module, keep working unchanged.
    """
    _inherit = 'res.partner'
