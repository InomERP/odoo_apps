# INOM Purchase Global Discount (Odoo 20)

Adds a **global discount** (percentage or fixed amount) on purchase orders.
The discount is distributed over the order lines through the native
`discount` field of `purchase.order.line`, so subtotals, taxes and vendor
bills keep working exactly like a manual line discount.

## Features
- Global discount type: *Percentage* or *Fixed Amount*, on the PO form
  (below the order lines).
- Fixed amounts are spread proportionally to each line total.
- Section / note lines are never discounted.
- Limits configured in *Purchase > Configuration > Settings*:
  - Maximum Allowed Discount (%)
  - Maximum Discount Amount
- Validation: a fixed discount cannot exceed the order lines total, and the
  configured maximums are enforced on save and on change.

## Security
The module adds fields to the existing `purchase.order` model only; access is
governed by the standard Purchase groups. It ships no access rows of its own.

## Tests
`odoo-bin -d <db> -i inom_purchase_global_discount --test-tags /inom_purchase_global_discount --stop-after-init`

## Changelog
- 20.0.1.0.0 - Migrated from Odoo 19 (see git history for details).
