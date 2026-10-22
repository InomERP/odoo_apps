# Real Estate Rental Management (`inom_rental_management`)

Odoo 19 Community module for property rental and sale management.
Release 19.0.1.7.0 covers:
- property management: details, image gallery, documents, availability and archiving rules;
- owners, tenants and buyers on standard Contacts: owned properties, rental history,
  confidential owner and tenant documents, role and relationship checks, and an optional
  rule that a tenant needs a valid identity document before a lease starts;
- property sales: CRM sale enquiries, booking, booking and balance invoices through standard
  Invoicing, credit notes on cancellation, invoice status from posted accounting entries,
  sale documents and a Sale Summary PDF;
- rental contracts: optional manager approval, start, expiry tracking with reminders,
  renewal, early termination, closing, no double letting (enforced server-side and safe under
  concurrent transactions), protected contract history and a contract calendar;
- rent and deposits: a billing schedule per lease, rent invoices through standard Invoicing
  (manual or by a daily job, draft unless automatic posting is enabled, never duplicated),
  overdue tracking from accounting, deposit invoices booked to the account of your deposit
  product, deposit settlement with deductions by credit note, and rent and deposit reports;
- enquiries: sale and rental enquiries as CRM opportunities linked to a property, a New Enquiry
  button with duplicate detection, the property's agent as responsible, automatic follow-up
  activity, enquiry status, conversion to a draft sale or lease (never automatic), and an
  Enquiry Analysis report;
- a dashboard (managers and accountants) with property, lease, rent and sale figures computed
  by aggregate queries, reports on rental income by property and owner, tenant outstanding
  invoices, contract expiry, occupancy and sale transactions, and daily To-Do reminders for
  rent due, overdue rent and pending enquiries (each created once).
Website and maintenance are separate modules: `inom_rental_management_website` and
`inom_rental_management_maintenance`.

Upgrade scripts in `migrations/` run automatically:
- 19.0.1.2.0 gives existing owners, tenants and buyers their role flag;
- 19.0.1.4.0 marks properties with a running lease as Rented.
Property and contract data is otherwise unchanged.

## Requirements

- Odoo 19.0 Community Edition
- Depends on `mail`, `account` and `crm` (all Community modules). Upgrading from
  19.0.1.2.0 installs CRM automatically.
- A chart of accounts (your localisation) is needed to create invoices.
- The products "Property Booking Amount", "Property Sale", "Rent", "Security Deposit" and
  "Deposit Deduction" are created without taxes: set the taxes and income accounts that apply
  to you, or pick other products in Settings. Give "Security Deposit" a liability account so
  deposits stay out of income; Settings warns while it does not have one.
- Leases started before 19.0.1.5.0 get no billing schedule automatically: a manager creates it
  with **Create Billing Schedule**, after setting **Invoice From** if earlier periods were
  already billed outside Odoo.

## Upgrading an existing database

Always name the database when upgrading, otherwise nothing is upgraded and the server fails
with "column ... does not exist":

```bash
./odoo-bin -c odoo.conf -d <database> -u inom_rental_management --stop-after-init
```

## Installation

1. Copy the `inom_rental_management` folder (or unzip `inom_rental_management.zip`) into a
   directory listed in your `addons_path`.
2. Restart the Odoo server.
3. Activate developer mode, open **Apps**, click **Update Apps List**.
4. Search for "Real Estate Rental Management" and click **Activate**.

From the command line instead:

```bash
./odoo-bin -c odoo.conf -d <database> -i inom_rental_management --stop-after-init
```

Upgrade after updating the code:

```bash
./odoo-bin -c odoo.conf -d <database> -u inom_rental_management --stop-after-init
```

## Demo data

Loaded only in databases created with demo data (`--with-demo`, or the Demo data box when creating
a database). It adds 11 properties with pictures (apartments, villas, a shop, an office, a plot), owners,
tenants and buyers, 6 rental contracts, 2 property sales and 4 enquiries. On install, the leases are
started and their rent is invoiced and mostly paid, with some overdue rent, a sold plot and a booked villa,
so the dashboard and reports show real figures. Invoices and payments need a chart of accounts; without
one the leases are only started. The Website and Maintenance add-ons add published listings and
maintenance requests.

The demo uses Indian addresses and rupee-sized amounts, in the company currency.

## Security groups

Set under **Settings > Users > Access Rights**, section *Real Estate* and *Real Estate Accounting*.

| Group | Inherits | Can do |
| --- | --- | --- |
| Property Agent | Internal User | Create, edit and archive properties; manage property images; create, start and renew own or unassigned contracts; close a lease once its end date has passed; read types and amenities |
| Property Manager | Property Agent | All contracts of all agents; approve leases; terminate or close leases early; delete properties and draft contracts; Reports menu |
| Real Estate Administrator | Property Manager | Configuration menu: property types and amenities. Given to the admin user on install |
| Accountant | Internal User, Invoicing | Read-only access to properties and all contracts; creates sale, rent and deposit invoices and deposit settlements; Rent and Reports menus; no access to owner and tenant documents |

All main models also have a multi-company record rule.

Owner and tenant documents (identity, address, tax, ownership, bank, agreements) are
confidential: agents see only the documents they uploaded and those of tenants and owners
on their own contracts and properties; managers and administrators see all; accountants
and other users see none. The tenant identity rule is under
**Real Estate > Configuration > Settings** (needs Settings access).

## Menus

Real Estate > Dashboard · Properties · Owners · Tenants · Documents · Rental Contracts ·
Enquiries (All, Rental, Sale; needs CRM access) · Rent (Rent Due, Billing Schedule, Rental Invoices, Deposit Status) ·
Property Sales (Sale Enquiries, Sale Contracts, Buyers) · Reports (Property, Rental, Sales, Enquiry Analysis,
Rental Income by Property, Rental Income by Owner, Tenant Outstanding Invoices, Contract Expiry,
Property Occupancy, Sale Transactions,
Rent Due, Overdue Rent, Paid Rent Invoices, Outstanding Rent Invoices, Deposit Status) ·
Configuration (Settings, Property Types, Amenities)

## Running the tests

```bash
./odoo-bin -c odoo.conf -d <new_test_db> -i inom_rental_management \
    --test-enable --test-tags=/inom_rental_management --stop-after-init
```
