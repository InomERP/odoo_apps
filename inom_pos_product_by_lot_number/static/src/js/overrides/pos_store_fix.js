/** @odoo-module **/
/*
 * ODOO 17: intentionally a no-op.
 *
 * The Odoo 18 version patched `processServerData` to backfill default config
 * flags. Odoo 17 has no `processServerData`, and its data loader exposes ALL
 * pos.config fields to the frontend (the iml_* flags included), so no backfill
 * is needed. Kept as an empty module so the assets glob stays stable.
 */
