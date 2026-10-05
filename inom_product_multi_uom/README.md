# INOM Product Multi Unit of Measure (Odoo 20)

Sell a single product in several Units of Measure.

- Product form: **Need Secondary UoMs** toggle and a *Secondary UoM's* table
  (UoM + ratio) edited through a popup wizard.
- Sale order lines: **Secondary Qty** and **Secondary UoM** columns next to the
  base Quantity / Unit. The base quantity is derived as
  `secondary qty x ratio`.
- Invoices: the invoice line keeps the correct base quantity and records the
  secondary UoM / quantity; the invoice PDF shows two extra columns only when
  at least one line uses a secondary UoM.
- Validation: duplicate secondary UoMs, a secondary UoM equal to the base UoM,
  a non-positive ratio and a secondary UoM that does not belong to the product
  are rejected.

## Security
`security/ir.access.csv` (Odoo 20 `ir.access`): internal users can read the
secondary UoM lines and use the wizard; Sales Managers can create, edit and
delete them.

## Tests
`odoo-bin -d <db> -i inom_product_multi_uom --test-tags /inom_product_multi_uom --stop-after-init`

## Changelog
- 20.0.4.4.0 - Migrated from Odoo 19 (new sale order line list structure,
  `models.Constraint`, `ir.access`, `Product Unit` decimal precision).
