"""Release the Pay action's registry key before this module claims it.

The button moved here from inom_fee_online so it exists whether or not the
online module is installed. Removing it from that module's data file does not
delete it from a database until *that* module is updated — and this one is
updated first, so the new record collides on the unique key and the whole
upgrade aborts.

A migration rather than a <function> in the data file: a migration runs before
any data is loaded, which is the only point at which the key is reliably free.
The data-file call ran too late to help on a database that already held the
old record.

Raw SQL rather than the ORM: at pre-migration the registry is the *old* one,
and reaching for a model method that only exists in the new code is how a
migration fails on the version it is meant to repair.
"""

import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        return          # fresh install: nothing to release

    cr.execute("""
        SELECT a.id, d.module, d.name
          FROM inom_portal_action a
          LEFT JOIN ir_model_data d
                 ON d.model = 'inom.portal.action' AND d.res_id = a.id
         WHERE a.key = 'fee.line.pay'
    """)
    rows = cr.fetchall()
    stale = [r for r in rows if r[1] != 'inom_fee']
    if not stale:
        return

    _logger.info('INOM fees: releasing "fee.line.pay" held by %s',
                 ', '.join(f'{module}.{name}' for _id, module, name in stale))

    ids = tuple(r[0] for r in stale)
    # The ir_model_data rows go first, or Odoo recreates the records the next
    # time the module that used to own them is updated.
    cr.execute("""DELETE FROM ir_model_data
                   WHERE model = 'inom.portal.action' AND res_id IN %s""", (ids,))

    # This table arrived in the same release as the migration, so on the
    # database being upgraded it may not exist yet. Checking beats assuming:
    # a migration that raises leaves the module half-updated.
    cr.execute("""SELECT 1 FROM information_schema.tables
                   WHERE table_name = 'inom_portal_action_input'""")
    if cr.fetchone():
        cr.execute("""DELETE FROM inom_portal_action_input
                       WHERE action_id IN %s""", (ids,))

    cr.execute("""DELETE FROM inom_portal_action WHERE id IN %s""", (ids,))
