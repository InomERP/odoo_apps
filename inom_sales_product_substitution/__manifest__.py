# -*- coding: utf-8 -*-
{
    "name": "Inom Sales Product Substitution",
    "version": "19.0.4.1.0",
    "category": "Sales/Sales",
    "summary": "Suggest and replace out-of-stock products with alternatives on "
               "sales orders.",
    "description": """
Sales Product Substitution
==========================

Phase 1 - Foundation
--------------------
* "Manage Alternative Products" setting in Sales configuration.
* "Alternative Products" relation on product variants (product.product).
* Automatic symmetric (reciprocal) synchronization of alternative links.
* Data integrity constraints (no self-reference, combo products excluded).

Phase 2 - Sales Order Integration
---------------------------------
* Alternatives smart button on the product form (count + drill-down).
* Computed stock availability on sales order lines with an insufficient-stock
  suggestion when alternatives exist.
* "Alternatives" button on each sales order line.
* Alternative-product replacement wizard showing the original product, its
  available quantity, the alternatives and their stock availability.
* One-click replacement of the line product, preserving quantity and using
  standard Odoo sales pricing.
* Access rights for Sales Users and Sales Managers.

Phase 3 - Replacement Wizard UI
-------------------------------
* Redesigned replacement wizard: original-product stat header (Internal
  Reference, Sales Price, Stock, General Stock) with a View Stock action.
* "Replacing Products" selection scoped to the configured alternatives.
* Alternative-products grid with Internal Reference, Product Name, Sales
  Price, Stock and General Stock columns plus a per-row View Stock action.
* Warehouse/location-wise stock popup for the original product and every
  alternative.

Phase 4 - Audit Log, Chatter & Replacement History
--------------------------------------------------
* Dedicated Product Substitution History model recording the order, line,
  original and replacement products, quantity, user, date and company.
* History records are created automatically on every replacement and kept as
  a read-only audit trail.
* A chatter message ("Product Substitution Completed") is posted on the sales
  order for each replacement.
* "Substitution History" smart button on the sales order showing the count and
  opening the related history.
* List, form and search views, a Reporting menu, security access and a
  multi-company record rule.

Phase 4.1 - Security Hardening
-----------------------------
* Reuses the standard Sales roles (Sales User, Sales Manager) and the
  Administrator group; no duplicate groups are created.
* Substitution History is a strict, immutable audit log: Sales User and Sales
  Manager have read-only access, only the Administrator has full access, and
  records are still created automatically (sudo) by the replacement wizard.
* Replacement wizard models grant read/write/create but no unlink (transient
  records are vacuumed by the system, not deleted by users).
* Canonical multi-company record rule scopes history visibility to the user's
  allowed companies.
""",
    "author": "InomERP",
    "website": "https://inomerp.in",
    "license": "LGPL-3",
    "depends": [
        "sale_management",
        "stock",
    ],
    "data": [
        "security/ir.model.access.csv",
        "security/inom_product_substitution_security.xml",
        "views/res_config_settings_views.xml",
        "views/product_template_views.xml",
        "views/product_product_views.xml",
        "wizard/inom_alternative_product_wizard_views.xml",
        "views/inom_product_substitution_history_views.xml",
        "views/sale_order_views.xml",
    ],
    'images': ['static/description/banner.png'],
    "installable": True,
    "application": False,
    "auto_install": False,
}
