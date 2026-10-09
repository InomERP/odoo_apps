# Inom Sale Order Merge — Odoo 20 migration

## Scope
This port preserves the existing merge workflows and business logic.

### Odoo 20 changes applied
- Manifest version updated to `20.0.5.0.0`.
- Replaced the Odoo 19 security file `security/ir.model.access.csv` with Odoo 20 `security/ir.access.csv`.
- Converted the four legacy CRUD columns to the Odoo 20 `operation` column (`crud` letters).
- Converted model references from `model_*` XML IDs to technical model names.
- Removed Python bytecode / `__pycache__` artifacts from the package.
- Existing wizard flows, merge behavior, automatic duplicate-line consolidation, menus, and settings remain unchanged.

## Functional areas preserved
1. Merge selected quotations into a new order.
2. Merge selected quotations into an existing selected order.
3. Same-customer merge wizard.
4. Cross-customer merge with an explicitly selected customer.
5. Cancel or delete source orders according to the selected merge mode.
6. Merge duplicate lines within one sale order.
7. Automatic duplicate-line consolidation when enabled in Sales settings.
8. Chatter/source tracking messages.

## Odoo 20 security format
`security/ir.access.csv` uses:
`id,name,model_id,group_id/id,operation,domain`

The module has no custom record-rule XML, so no separate `ir.rule` migration was required.
