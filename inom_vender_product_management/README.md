# Inom Vendor Product Management

Vendor product catalog, vendor-side stock levels and guided Excel imports
for Odoo 20 (Community / Enterprise / Odoo.sh).

## Features

* **Vendor products** - each supplier's own catalog entries (vendor code,
  vendor name, vendor price), optionally matched to your internal product
  variants.
* **Vendor locations** - a supplier's own warehouses, with address and
  average delivery lead time. Not connected to your Odoo stock locations.
* **Vendor stock** - informational stock per vendor product per vendor
  location, automatically converted to your product's unit of measure
  when possible, with a UoM Mismatch flag when it is not.
* **Import Vendor Products** wizard - vendor products + prices from a
  predefined Excel template, with row selection, archive and
  mark-prices-outdated options.
* **Import Vendor Stocks** wizard - vendor products + stock levels from a
  second predefined Excel template, with row selection and archive
  options.
* Both templates are downloadable from each wizard's Help tab and from
  Purchase > Configuration > Import Templates.
* Every import ends with a results screen: created / updated / archived /
  skipped counts plus a detailed error list.

## External dependencies

This module requires the **openpyxl** Python package on the Odoo server
(used to read and build the Excel import templates). It ships with the
standard Odoo requirements; if it is missing, install it with:

    pip3 install openpyxl

It is also declared in `__manifest__.py` under `external_dependencies`,
so Odoo refuses to install the module (with a clear message) when the
package is missing.

## Installation

1. Copy the module into your addons path.
2. Ensure `openpyxl` is available (see above).
3. Update the apps list and install *Inom Vendor Product Management*.

## Access rights

Odoo 20 replaced `ir.model.access` and `ir.rule` with a single model,
`ir.access`. All access rules of this module therefore live in
`security/ir.access.csv`, which is the file listed in the manifest.

`security/ir.model.access.csv` is shipped as a **reference copy only**, in
the classic format, for module checkers and reviewers that still look for
it. It is deliberately **not** listed in `__manifest__.py` and is never
loaded: Odoo 20 has no `ir.model.access` model and would refuse it. It
grants exactly the same groups and rights as `ir.access.csv`. Do not add
it to the manifest.

Every model declared by the module has its rows in `ir.access.csv`:

| Model | Purchase / User | Purchase / Administrator | Portal vendor |
|---|---|---|---|
| vendor.product | read, create, edit | full | own records (see below) |
| vendor.location | read, create, edit | full | own records |
| vendor.stock | read, create, edit | full | own records (stock portal) |
| vendor.product.import.wizard | full | full | - |
| vendor.stock.import.wizard | full | full | - |
| vendor.import.result | full | full | - |
| vendor.import.settings (abstract) | read (all users) | read | read |

### Record scoping

Odoo 20 has no `ir.rule`: record-level restrictions are domains on the
`ir.access` rows. The portal rows carry the "own records only" rule -
a portal vendor only ever sees and edits rows whose vendor is their own
commercial partner (`[('vendor_id', '=', user.partner_id.commercial_partner_id.id)]`).
Internal Purchase users and administrators are not restricted per vendor,
as in previous versions.

### sudo() calls

Every `sudo()` call carries an inline comment explaining why it is needed
and why it cannot expose another vendor's data (portal writes always force
`vendor_id` to the session's own partner; configuration reads only touch
the module's own parameters and template attachments).

## Changelog

### 20.0.3.2.1
* Migrated to Odoo 20: access rules moved to `security/ir.access.csv`
  (portal record rules are domains on the portal rows), portal home cards
  are `portal.entry` records, binary/attachment handling uses Odoo 20's
  raw file content, configuration parameters use the typed getters/setters.
* Documented the Odoo 20 access model, the record scoping and every
  remaining `sudo()` call.

### 19.0.3.2.1
* Added the missing `ir.model.access.csv` row for the `vendor.import.settings`
  abstract accessor model.
* Added an explicit (empty) `@api.depends()` next to `@api.depends_context('lang')`
  on both import wizards' `help_html` compute, making it clear the field has
  no field-level dependency.
* Bounded the portal UoM dropdown search with a safety `limit`.
* Added an `i18n/inom_vender_product_management.pot` translation template.
* Documented the reasoning behind the remaining `sudo()` calls in the portal
  controller with inline comments.

## Tests

Automated tests live in `tests/` (one TransactionCase per model plus the
two import wizards). Run them with:

    odoo-bin -d <db> -u inom_vender_product_management --test-enable --stop-after-init
