"""Rename res.partner.x_check_credit to x_enforce_credit_limit.

Moves the existing column and its field metadata so each customer's
setting is kept on upgrade instead of being reset to the default.
"""


def migrate(cr, version):
    if not version:
        return
    cr.execute("""
        SELECT 1 FROM information_schema.columns
         WHERE table_name = 'res_partner' AND column_name = 'x_check_credit'
    """)
    old_exists = cr.fetchone()
    cr.execute("""
        SELECT 1 FROM information_schema.columns
         WHERE table_name = 'res_partner' AND column_name = 'x_enforce_credit_limit'
    """)
    new_exists = cr.fetchone()
    if not old_exists or new_exists:
        return
    cr.execute(
        "ALTER TABLE res_partner RENAME COLUMN x_check_credit TO x_enforce_credit_limit"
    )
    cr.execute("""
        UPDATE ir_model_fields
           SET name = 'x_enforce_credit_limit'
         WHERE model = 'res.partner' AND name = 'x_check_credit'
    """)
    cr.execute("""
        UPDATE ir_model_data
           SET name = 'field_res_partner__x_enforce_credit_limit'
         WHERE module = 'inom_customer_credit_limit'
           AND model = 'ir.model.fields'
           AND name = 'field_res_partner__x_check_credit'
    """)
