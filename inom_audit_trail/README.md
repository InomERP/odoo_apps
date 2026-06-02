# Audit Trail (Odoo 19)

Rule-based audit trail for Odoo 19. Configure **what** to track and get a clean
log of **who** did **what**, **when** — including field-level *old → new* values.

## Features

- **Logging rules per object (model).** Choose an Odoo object and which operations
  to log: Create, Read, Update, Delete.
- **Field-level tracking.** On Update, pick the exact fields to watch
  (e.g. on `res.partner`: Name, Email, Phone). Each change is stored with the
  user, the previous value and the new value. Leave the field list empty to
  track every field.
- **Group restriction.** Optionally log only actions performed by users in a
  given group.
- **Audit Log** with badges per operation, search, group-by and a detail form
  showing the tracked field changes.
- **Live Overview dashboard** (OWL): active users right now (from `bus.presence`),
  today's activity vs yesterday with an hourly mini-chart, and active-rule count.

## Install

1. Copy the `inom_audit_trail` folder into your Odoo `addons` path.
2. Update the apps list and install **Audit Trail**.
3. Open the **Audit Trail** app → **Configuration → Logging Rules** and add a rule.

Requires Odoo **19.0** (depends on `base`, `web`, `bus`).

## How it works

A lightweight extension of the global `base` model intercepts `create` /
`read` / `write` / `unlink`. For every operation it checks (via a cached
lookup) whether an active rule covers that model + operation + the acting
user's group, and—for updates—whether a tracked field actually changed. Only
then is a log written. Models with no rule incur effectively no overhead.

## Notes & caveats

- **Read logging is high-volume.** It is off by default and should be enabled
  only for sensitive objects; Odoo reads records constantly to render views.
- The audit models themselves are never logged (no recursion).
- Field values are stored as human-readable strings (e.g. a many2one shows its
  display name), not raw IDs.
- For very high-throughput databases, consider archiving/rotating
  `inom.audit.trail.log` periodically.

## License

LGPL-3
