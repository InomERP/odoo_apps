# -*- coding: utf-8 -*-
from . import models
from . import controllers


def _post_init_set_groups(env):
    """
    Post-install hook.

    Grant the "Allow Create Lot/Serial Number from POS" privilege to
    existing POS Managers by linking `point_of_sale.group_pos_manager`
    with our new `group_pos_lot_create` via `implied_ids`.

    Done in Python (rather than from XML) so we don't depend on the
    fragile cross-module XML update path that, on Odoo 19, was causing
    `ir.model.access.csv` to fail to resolve our group's external id
    during initial install.

    Idempotent: safe to call on re-install / upgrade.
    """
    pos_manager = env.ref(
        'point_of_sale.group_pos_manager',
        raise_if_not_found=False,
    )
    lot_create = env.ref(
        'inom_pos_product_by_lot_number.group_pos_lot_create',
        raise_if_not_found=False,
    )
    if pos_manager and lot_create and lot_create not in pos_manager.implied_ids:
        pos_manager.sudo().write({'implied_ids': [(4, lot_create.id)]})
