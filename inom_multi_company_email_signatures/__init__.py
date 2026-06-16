# -*- coding: utf-8 -*-
from . import models


def post_init_hook(env):
    """Migrate existing res.users.signature values into new sub-table."""
    Sig = env['res.users.signature'].sudo()

    # Read raw column directly from DB (bypasses our compute override)
    env.cr.execute(
        "SELECT id, company_id, signature FROM res_users "
        "WHERE signature IS NOT NULL AND signature != ''"
    )
    for user_id, company_id, signature in env.cr.fetchall():
        if not company_id:
            continue

        existing = Sig.search([
            ('user_id',    '=', user_id),
            ('company_id', '=', company_id),
        ], limit=1)

        if existing:
            existing.write({'signature': signature})
        else:
            Sig.create({
                'user_id':    user_id,
                'company_id': company_id,
                'signature':  signature,
            })