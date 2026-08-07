# Server Health Monitor

Live host, PostgreSQL and Odoo metrics inside Odoo, built so that watching the
server does not become the thing slowing it down.

## Requirements

| Requirement | Why |
|---|---|
| Odoo 18.0 Community or Enterprise | Target release. |
| **`psutil`** (Python package) | Worker enumeration and the memory fallback. Install it on the server *before* installing or upgrading the module. |
| Linux host with `/proc` and `/sys` readable | CPU, memory, load and uptime come from there. |
| PostgreSQL role that can read `pg_stat_activity` | Connection and query metrics. `pg_monitor` widens this to non-Odoo sessions. |

```bash
# in the same virtualenv Odoo runs from
pip install psutil
```

`psutil` is declared in the manifest under `external_dependencies`, so Odoo
refuses to install the module without it rather than failing halfway through.
That check runs at install time on the machine doing the install — if you run
several Odoo nodes, every node needs the package.

Without `psutil` the module will not install. Everything else degrades
gracefully: a missing `pg_monitor` grant, an absent `pg_stat_statements`, or a
container that hides sibling processes each disable one panel and say so in
the UI.


## The performance contract

| Concern | How it is handled |
|---|---|
| Blocking calls | `psutil.cpu_percent(interval=1)` is never used. CPU comes from a delta read of `/proc/stat` (~20 µs). |
| DB round trips | One combined query for all live PostgreSQL metrics. |
| Expensive probes | `pg_database_size` cached 60 s. Table bloat, `pg_stat_statements` and filestore size walks are cron-only or excluded entirely. |
| Writes per poll | Zero. The endpoint is read-only and sets `save_session=False`. History is written by cron at a fixed rate, independent of how many dashboards are open. |
| Stacking requests | Single-flight guard: if a collection is in progress, concurrent callers get the cached value instead of queueing. |
| Idle dashboards | Polling pauses on `visibilitychange`. A forgotten background tab costs nothing. |
| Server trouble | Exponential backoff to 2 min on error, so a restarting server is not hammered. |
| Poll storms | `setTimeout` chain, not `setInterval`. Interval is server-configured and floored at 3 s. |
| Self-observation | Every response carries `collect_ms`, shown in the header. A warning is logged if collection exceeds 150 ms. |

Measured cost of the full host probe: **~0.17 ms**.

## Access control

Two groups, under **Server Health** in user settings:

| Group | Can |
|---|---|
| Viewer | Read the live dashboard, history and alerts. Read-only everywhere. |
| Manager | Everything a Viewer can, plus create and edit alert rules. |

Reading a CPU graph should not require the right to install modules, so this
is deliberately separate from Settings access. Existing Settings users are
granted Manager automatically on upgrade, so nobody loses access.

Nothing is visible to a plain internal user: both HTTP endpoints check the
Viewer group before collecting anything, and every menu carries an explicit
`groups=`. That last part matters — the Live dashboard is an
`ir.actions.client` with no model behind it, so Odoo cannot infer access from
the action. Without the explicit gate, every internal user would see the app
in the switcher and hit a 403 on opening it.

## Configuration

| Parameter | Default |
|---|---|
| `inom_server_health.poll_interval_s` | `10` |
| `inom_server_health.retention_days` | `30` |

Optional, for full visibility:

```sql
GRANT pg_monitor TO odoo;
```

## Known limits

- **Self-hosted only.** Odoo.sh and Odoo Online give no `/proc` access and a
  restricted PostgreSQL role. The module has nothing useful to show there.
- **Containers.** Memory and CPU are both cgroup-aware. When a CPU quota is in
  force, CPU percent is the container's own consumption as a share of its
  quota (from `cpu.stat` / `cpuacct.usage`), not the host's utilisation. With
  no quota it falls back to host-wide `/proc/stat`.
- **Without `pg_monitor`**, `pg_stat_activity` only exposes Odoo's own
  sessions. Non-Odoo connections are invisible. The UI says so.
- **`pg_stat_statements`** needs `shared_preload_libraries` and a PostgreSQL
  restart. Odoo cannot enable it; the module detects and degrades.
- **Worker enumeration** relies on `psutil` and on sibling processes being
  visible. Some hardened container runtimes hide them.
- **The `mail_mail` index** is created without `CONCURRENTLY` because module
  installation runs in a transaction. On a very large `mail_mail` this briefly
  locks writes — build it by hand out of hours if that matters.
- **Multi-server deployments** are not aggregated in v1. Each node reports
  itself; history rows carry a `node` column so v3 can group them.


## Alerting

Rules are evaluated inside the sampling cron against the row just written —
no extra probes, no extra host queries.

Two properties matter more than the thresholds:

- **Debounce** — a rule fires only after N consecutive breaching samples. A
  single spike during a backup is not an incident, and an alerting system that
  cannot tell the difference gets muted within a week.
- **Cooldown** — once notified, a rule stays quiet for its cooldown window
  even while still breaching. Without it a two-hour incident sends 24
  identical emails and nobody reads any of them.

Recovery is deliberately asymmetric: one clean sample resolves an alert. You
should not have to wait out another debounce window to learn it is over.

Notification routes to email, a Discuss channel, or a webhook. Every route is
wrapped — a dead mail server or an unreachable webhook must never roll back
the sample that triggered it, or wedge the sampling cron.

Eight starter rules ship enabled with conservative thresholds. They notify
nobody until you add recipients.

### Alerting caveats

- **Resolution is capped by the sampling interval.** At the default 5-minute
  cron, a rule with a debounce of 3 needs 15 minutes to fire. Lower the cron
  interval if you need faster detection, and accept the extra rows.
- **The webhook call is blocking**, inside the cron, with a 5 s timeout. A
  slow endpoint delays that cron run.
- **`breach_streak` lives on the rule**, so in a multi-node deployment all
  nodes share one streak counter. Correct for single-node; wrong for several.
  Multi-node alerting needs the streak keyed by node.
- **No escalation, no acknowledgement, no on-call rotation.** If an alert
  opens and nobody looks, it just sits there until it resolves itself.


## Tests

```bash
odoo-bin -d <database> -i inom_server_health --test-enable --test-tags /inom_server_health
```

Three suites, all `TransactionCase`:

| File | Covers |
|---|---|
| `tests/test_alerting.py` | Debounce, cooldown, recovery, second-alert-after-recovery, peak tracking for both operators, multi-rule evaluation in one pass, open alert counting, inactive rules, and the Viewer/Manager access split. |
| `tests/test_sampling.py` | The collector payload to column mapping, degradation to zeros when a probe block is missing, one row per capture, and retention vacuuming. |
| `tests/test_probes.py` | Every probe executed against the real cursor, including the parameterised cron and presence windows, a forced late cron, and a full `collect()` fed straight into the sample model. |

`tests/test_probes.py` exists specifically so the parameterised SQL is
executed rather than merely inspected: it forces a late `ir.cron` row so the
late-rows statement runs, and asserts that a narrower window really does
report a larger backlog than a wider one — which fails if a bind parameter is
ever ignored.


## dev-tools

`dev-tools/verify_views.py` validates every view arch against Odoo 18.0's own
RNG schemas (vendored from `odoo/addons/base/rng/` on the 18.0 branch). Run it
before packaging:

```
python3 dev-tools/verify_views.py
```

It exists because an earlier revision shipped a search view using
`<group expand="0" string="Group By">`. `search_view.rng` allows `<group>`
neither attribute and requires its children to be `<field>`, so the upgrade
failed with a bare "Invalid view definition". The schema says exactly what is
wrong; guessing does not.

Note: Odoo 18.0 ships no RNG for form views — those are validated in Python at
load time, so this script cannot check them.

`dev-tools/verify_review_rules.py` is an offline replica of the static review
checks (SEC-004, PERF-001, PERF-010, ORM-005, ORM-012, MNT-021). Run it before
packaging so a regression surfaces here rather than in the next review:

```
python3 dev-tools/verify_review_rules.py
```

`dev-tools/make_pot.py` regenerates `i18n/inom_server_health.pot` statically.
`odoo-bin --i18n-export` against an installed database remains authoritative;
this exists so the template is present and current without a running server.

### Why the alert writes look the way they do

`_apply_evaluation` batches everything that shares a value into one `write()`,
then assigns the genuinely per-record values -- a streak counter, a last
value, a peak -- directly on the record.

That is not a style choice. In Odoo 18 a stored-field write does not issue
SQL: `Field.write` updates the cache and marks the record dirty, and the flush
later hands every dirty record to `_write_multi`, which emits a single
`UPDATE ... FROM (VALUES ...)` per distinct *set of columns* -- not per
distinct value. Assigning on the record and calling `write()` therefore reach
the database as exactly the same statements, and the assignment form drops a
redundant `browse()` per group.

A static checker cannot see flush behaviour, so a loop containing `write()`
here reads as "one query per iteration" when it never was. The evaluation
pass costs: one rule read, one open-alert read, one `create` for newly opened
alerts, and one UPDATE per column set at flush -- regardless of how many
rules are configured.

### The one core patch: `static/src/js/hour_interval.js`

The History graph buckets by hour. On this release the ORM supports that
granularity -- `READ_GROUP_TIME_GRANULARITY` in `odoo/models.py` lists `hour`
and `READ_GROUP_DISPLAY_FORMAT` carries its label format -- but the web client
does not: `getGroupBy` validates the interval against `INTERVAL_OPTIONS`
(`web/static/src/search/utils/dates.js`), which stops at `day`. A view arch
asking for `interval="hour"` therefore throws *"Invalid groupBy description:
sampled_at:hour"* client-side, before any RPC.

Odoo 19 solved this by splitting the constant: `INTERVAL_OPTIONS` still drives
the Group By dropdown, and a separate `BACKEND_INTERVAL_OPTIONS` (the same plus
`hour`) is what `getGroupBy` validates against. So `hour` is accepted from a
view arch but is *not* offered as a menu option on every date field.

`hour_interval.js` reproduces that split on Odoo 18.0: it appends `hour` to
`INTERVAL_OPTIONS` (last, so `rankInterval` keeps the coarse-to-fine ordering),
then patches `SearchModel.setup` to filter it back out of `intervalOptions`,
the array that populates the dropdown. Without the second step this module
would add an "Hour" entry under every date field in every app in the database.

It is the only place this module touches core behaviour, and the effect is
scoped to this module's own graph view. If you would rather not carry it,
delete the file, drop its line from `__manifest__.py` and set
`interval="day"` on the `sampled_at` field in `views/health_views.xml`; nothing
else depends on it.

