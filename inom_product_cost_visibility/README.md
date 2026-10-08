# INOM Product Cost Visibility — Odoo 20

## Purpose
Users in `View Product Cost` can see the Product Cost (`standard_price`) while users outside the group cannot.

## Odoo 20 migration changes
- Version bumped to `20.0.1.0.0`.
- Product Template form now inherits `product.product_template_form_view`.
- Product Variant form continues through `product.product_normal_form_view`.
- Product Variant list uses `product.product_product_tree_view`.
- Removed the V19 quick-edit view inheritance because `product.product_variant_easy_edit_view` is not present in Odoo 20.
- Removed the V19 Product Template list inheritance because the Odoo 20 core Product Template list does not contain `standard_price`.
- Added the Odoo 20 Product Variant kanban cost restriction.
- Security privilege/group structure is retained.

## Functional test
1. Administrator/backend: install or upgrade the module.
2. Administrator/backend: Settings → Users & Companies → Users → create two internal users:
   - Cost User: add `View Product Cost`.
   - No Cost User: do not add `View Product Cost`.
3. Administrator/backend: Products → Products → open a product.
   - Cost User: Cost field/group is visible.
   - No Cost User: Cost/Pricing group containing Cost is hidden.
4. Administrator/backend: open Products → Product Variants list.
   - Cost User: Cost column is visible.
   - No Cost User: Cost column is hidden.
5. Administrator/backend: open a product variant kanban view where cost is shown.
   - Cost User: Cost is visible.
   - No Cost User: Cost is hidden.
6. Administrator/backend: verify Administrator/system user still sees Cost because `base.group_system` implies the module group.
