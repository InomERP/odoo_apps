# Real Estate Rental Management - Maintenance (`inom_rental_management_maintenance`)

Property maintenance on standard Odoo Maintenance: requests are ordinary
`maintenance.request` records linked to a property and, optionally, its lease.
Kept as a separate module so the core module does not require the Maintenance app.

## Requirements

- Odoo 19.0 Community Edition
- `inom_rental_management` and `maintenance`

## Installation

```bash
./odoo-bin -c odoo.conf -d <database> -i inom_rental_management_maintenance --stop-after-init
```

Upgrade later with `-u inom_rental_management_maintenance`, always with `-d <database>`.

## What it adds

- Property, lease and tenant on maintenance requests; Maintenance Request buttons and
  counters on properties and leases; a Real Estate > Maintenance menu.
- Per-property default team and responsible person.
- Access: agents see requests of their properties, managers all property requests,
  accountants read them; other employees keep the standard "own requests" access and
  cannot link requests to properties.
- History: started property requests cannot be deleted (archive them); properties with
  maintenance history cannot be deleted.
- Costs: cost and who bears it (company, owner, tenant), set by Property or Maintenance
  managers; Charge Cost creates a standard customer invoice with the
  "Maintenance Recharge" product (configurable in Settings).
- Reminders: the responsible person gets one To-Do for property work scheduled within the
  reminder window (1 day by default, in Settings), again only if it is rescheduled.
- Reports > Maintenance Summary: property requests by property and stage, with cost and duration.
