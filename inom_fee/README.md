# University — Fees (`inom_fee`)

Part of the INOM University Management System for Odoo 20 (Community and Enterprise).

Fee structures, components, instalment schedules, scholarships and a per-student
fee account, built on top of Odoo accounting.

## What it does

- **Fee structures** per programme, quota and academic year, made of component
  heads (tuition, examination, library, laboratory, ...). Instalment percentages
  must total 100% before a structure can be published.
- **Scholarships and waivers** as a percentage of the total or a fixed amount
  (capped at the gross fee).
- **Student fee accounts**: one per student per academic year, holding the
  dated instalment schedule generated from the structure.
- **Automatic account on enrolment**: enrolling a student raises their fee
  account and schedule from the published structure for their programme and
  year (general quota preferred). A missing structure never blocks enrolment;
  it is logged instead.
- **Invoicing**: issuing an instalment creates a posted customer invoice
  (`account.move`); payments are ordinary `account.payment` records, so the fee
  ledger and the trial balance can never disagree.
- **Reports**: fee structure sheet, student fee statement and fee receipt,
  served through the portal report controller with the caller's own rights.

## Dependencies

`inom_portal`, `inom_student`, `account`, `account_payment`.

## Running the tests

```bash
odoo-bin -d <db> -u inom_fee --test-enable --test-tags /inom_fee --stop-after-init
```

The tests build their own institution, programme, year and structures, so they
run on an empty database as well as one seeded with demo data.

## Translations

`i18n/inom_fee.pot` is the translation template. Regenerate it after changing
any user-facing string:

```bash
odoo-bin i18n export -d <db> -o inom_fee/i18n/inom_fee.pot inom_fee
```

## Licence

LGPL-3. Published by InomERP Pvt Ltd — https://inomerp.in — info@inomerp.in
