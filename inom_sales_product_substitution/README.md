# Sales Product Substitution

**Technical name:** `inom_sales_product_substitution`
**Version:** 19.0.1.0.0
**Author:** InomERP (https://inomerp.in)
**License:** LGPL-3
**Target:** Odoo 19 (Community & Enterprise)

## Scope of this release — Phase 1 (Foundation Layer)

This release delivers only the foundation/data layer:

- **Settings toggle** — *Sales → Configuration → Settings → Alternative Products → Manage Alternative Products*.
- **Alternative Products** relation on product variants (`product.product.inom_alternative_product_ids`).
- **Reciprocal synchronization** — links are kept symmetric automatically; a group of linked products becomes mutually alternative (recursion-guarded, non-destructive).
- **Constraints** — a product cannot be its own alternative; products of type *Combo* are excluded.
- **Conditional visibility** — the Alternatives section appears only when the setting is enabled.

## Not in this release (later phases)

Sale order integration, alternative-product wizard, product replacement, warehouse stock wizard, chatter logging, reporting, dashboards and future enhancements.

## Install

1. Copy the module into your addons path.
2. Restart Odoo and update the apps list.
3. Install **Sales Product Substitution** (`stock` and `sale_management` install automatically).

## Configure & use

1. Enable *Manage Alternative Products* in Sales settings.
2. Open a product variant, go to the **Alternatives** tab, and add substitute products. Reverse links are created automatically.
