# Real Estate Rental Management Suite (`inom_rental_management_suite`)

Bundle module for Odoo 19 Community. Installing it installs the complete real estate
package in one step. It adds no models, views or data of its own.

| Module | Technical name | What it adds |
| --- | --- | --- |
| Real Estate Rental Management | `inom_rental_management` | Properties, owners, tenants and buyers, rental contracts, rent invoicing, security deposits, property sales, CRM enquiries, dashboard and reports |
| Real Estate Rental Management - Website | `inom_rental_management_website` | Public property listing with filters, property pages, brochure links and an enquiry form creating CRM enquiries |
| Real Estate Rental Management - Maintenance | `inom_rental_management_maintenance` | Maintenance requests linked to properties and leases, cost tracking and recharge to tenant or owner |

## Requirements

- Odoo 19.0 Community Edition
- The three modules above in your `addons_path` (the suite depends on all of them).
  Standard Odoo apps they pull in: `mail`, `account`, `crm`, `website_crm`, `maintenance`.

## Installation

1. Copy `inom_rental_management_suite` together with `inom_rental_management`,
   `inom_rental_management_website` and `inom_rental_management_maintenance` into a directory
   listed in your `addons_path`.
2. Restart the Odoo server.
3. Activate developer mode, open **Apps**, click **Update Apps List**.
4. Search for "Real Estate Rental Management Suite" and click **Activate**.

From the command line instead:

```bash
./odoo-bin -c odoo.conf -d <database> -i inom_rental_management_suite --stop-after-init
```

## Upgrading

The suite has nothing to migrate. Upgrade the modules themselves, always naming the
database:

```bash
./odoo-bin -c odoo.conf -d <database> -u inom_rental_management,inom_rental_management_website,inom_rental_management_maintenance --stop-after-init
```

## Uninstalling

Uninstalling the suite only removes the bundle. The three modules stay installed with
all their data; uninstall them separately if you want them removed.
