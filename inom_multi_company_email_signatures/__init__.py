# -*- coding: utf-8 -*-
from . import models


def post_init_hook(env):
    """Migrate existing res.users signature values into the per-company table.

    Done in a single set-based query: the raw ``res_users.signature`` column is
    read directly (bypassing our compute override) and upserted for each
    user's default company.
    """
    env.cr.execute("""
        INSERT INTO res_users_signature
               (user_id, company_id, signature,
                create_uid, write_uid, create_date, write_date)
        SELECT u.id, u.company_id, u.signature,
               %(uid)s, %(uid)s, NOW() AT TIME ZONE 'UTC', NOW() AT TIME ZONE 'UTC'
          FROM res_users u
         WHERE u.company_id IS NOT NULL
           AND u.signature IS NOT NULL
           AND u.signature != ''
        ON CONFLICT (user_id, company_id) DO UPDATE
           SET signature  = EXCLUDED.signature,
               write_uid  = EXCLUDED.write_uid,
               write_date = EXCLUDED.write_date
    """, {'uid': env.uid})
    env['res.users.signature'].invalidate_model()
