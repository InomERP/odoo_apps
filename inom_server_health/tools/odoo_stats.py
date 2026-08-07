# -*- coding: utf-8 -*-
"""Odoo-layer metrics.

This is the part a generic server monitor cannot give you: which cron is
behind, how deep the mail queue is, and how fat each worker has grown against
its recycle limit.
"""

import logging
import os

_logger = logging.getLogger(__name__)

try:
    import psutil
except ImportError:  # pragma: no cover
    psutil = None


def _column_exists(cr, table, column):
    cr.execute("""
        SELECT 1 FROM information_schema.columns
         WHERE table_name = %s AND column_name = %s
    """, (table, column))
    return bool(cr.fetchone())


# Two complete literal statements rather than one built by interpolation.
# `failure_count` is a column name, not a value, so it cannot be passed as a
# bind parameter -- and building the statement with % would put a formatted
# string into cr.execute(). Selecting between fixed literals keeps every
# statement in this module free of string formatting, and the only variable
# part (the lateness window) travels as a real parameter.
_CRON_TOTALS_WITH_FAILURES = """
    SELECT count(*) FILTER (WHERE active)                       AS active_count,
           count(*) FILTER (
               WHERE active AND nextcall < (now() at time zone 'UTC')
                                          - interval '1 minute' * %s)
                                                                 AS late_count,
           count(*) FILTER (WHERE active AND failure_count > 0)  AS failing_count
      FROM ir_cron
"""

_CRON_TOTALS_PLAIN = """
    SELECT count(*) FILTER (WHERE active)                       AS active_count,
           count(*) FILTER (
               WHERE active AND nextcall < (now() at time zone 'UTC')
                                          - interval '1 minute' * %s)
                                                                 AS late_count,
           0                                                     AS failing_count
      FROM ir_cron
"""

_CRON_LATE_ROWS = """
    SELECT c.id, c.cron_name, c.nextcall,
           EXTRACT(EPOCH FROM (now() at time zone 'UTC') - c.nextcall)
               AS behind_s
      FROM ir_cron c
     WHERE c.active
       AND c.nextcall < (now() at time zone 'UTC')
                        - interval '1 minute' * %s
     ORDER BY c.nextcall ASC
     LIMIT 10
"""


def crons(cr, late_after_minutes=5):
    """Small table, indexed -- cheap. Cached ~15 s by the caller."""
    # Cast first: the window is the only caller-supplied value in these
    # statements, and it travels as a bind parameter, but rejecting a
    # non-numeric window here means it never reaches the database at all.
    window = int(late_after_minutes)
    has_failure_count = _column_exists(cr, "ir_cron", "failure_count")
    cr.execute(
        _CRON_TOTALS_WITH_FAILURES if has_failure_count else _CRON_TOTALS_PLAIN,
        (window,))
    row = cr.dictfetchone() or {}

    late = []
    if row.get("late_count"):
        cr.execute(_CRON_LATE_ROWS, (window,))
        late = [{
            "id": r["id"],
            "name": r.get("cron_name") or "(unnamed)",
            "behind_s": int(r.get("behind_s") or 0),
        } for r in cr.dictfetchall()]

    return {
        "active_count": row.get("active_count") or 0,
        "late_count": row.get("late_count") or 0,
        "failing_count": row.get("failing_count") or 0,
        "late": late,
    }


def mail_queue(cr):
    """Cached 30 s by the caller.

    Caveat: mail_mail has no index on `state` in stock Odoo. On instances with
    a large retained mail history this is a sequential scan. The module ships
    a partial index in data/ to make it cheap; if you removed it, raise the
    cache TTL.
    """
    cr.execute("""
        SELECT count(*) FILTER (WHERE state = 'outgoing')  AS outgoing,
               count(*) FILTER (WHERE state = 'exception') AS failed
          FROM mail_mail
         WHERE state IN ('outgoing', 'exception')
    """)
    row = cr.dictfetchone() or {}
    return {
        "outgoing": row.get("outgoing") or 0,
        "failed": row.get("failed") or 0,
    }


def _table_exists(cr, table):
    cr.execute("SELECT to_regclass(%s)", (table,))
    row = cr.fetchone()
    return bool(row and row[0])


def active_users(cr, active_window_minutes=30):
    """Who is actually working right now.

    Source is mail.presence -- renamed from bus.presence in Odoo 19, verified
    against addons/mail/models/mail_presence.py on the 19.0 branch. It is a
    one-row-per-user table with unique indexes on user_id, so this is cheap
    even on a large user base.

    Concurrency is the number that explains load: 4 users and 400 users
    produce very different graphs from identical hardware, and without this
    the dashboard can tell you the server is busy but never why.
    """
    # Cast before probing, for the same reason as in crons().
    window = int(active_window_minutes)
    if not _table_exists(cr, "mail_presence"):
        return {"available": False, "online": 0, "away": 0, "recent": 0,
                "users": []}

    cr.execute("""
        SELECT count(*) FILTER (WHERE p.status = 'online')  AS online,
               count(*) FILTER (WHERE p.status = 'away')    AS away,
               count(*) FILTER (
                   WHERE p.last_poll > (now() at time zone 'UTC')
                                       - interval '1 minute' * %s)  AS recent
          FROM mail_presence p
         WHERE p.user_id IS NOT NULL
    """, (window,))
    totals = cr.dictfetchone() or {}

    # The roster is capped -- this is a health panel, not a staff directory.
    cr.execute("""
        SELECT u.id AS user_id,
               p.status,
               EXTRACT(EPOCH FROM (now() at time zone 'UTC') - p.last_presence)
                   AS idle_s
          FROM mail_presence p
          JOIN res_users u ON u.id = p.user_id
         WHERE p.status IN ('online', 'away')
           AND u.active
         ORDER BY p.last_presence DESC
         LIMIT 20
    """)
    rows = cr.dictfetchall()
    return {
        "available": True,
        "online": totals.get("online") or 0,
        "away": totals.get("away") or 0,
        "recent": totals.get("recent") or 0,
        "user_ids": [r["user_id"] for r in rows],
        "rows": rows,
    }


def workers(limit_memory_hard=None):
    """Walks only this process's siblings -- not the full process table.

    psutil.process_iter() over every PID on the host is expensive; children()
    of our own parent is not.
    """
    if psutil is None:
        return {"available": False, "items": []}
    try:
        me = psutil.Process(os.getpid())
        master = me.parent() or me
        procs = [master] + master.children(recursive=False)
    except Exception:
        _logger.debug("Could not enumerate workers", exc_info=True)
        return {"available": False, "items": []}

    items = []
    for proc in procs:
        try:
            with proc.oneshot():
                rss = proc.memory_info().rss
                items.append({
                    "pid": proc.pid,
                    "rss": rss,
                    "threads": proc.num_threads(),
                    "is_master": proc.pid == master.pid,
                    "hard_limit_pct": (
                        round(100.0 * rss / limit_memory_hard, 1)
                        if limit_memory_hard else None
                    ),
                })
        except Exception:
            continue
    items.sort(key=lambda i: (not i["is_master"], -i["rss"]))
    return {"available": True, "items": items[:32]}


def config_limits():
    """Odoo's own caps -- the numbers RSS should be compared against."""
    try:
        from odoo.tools import config
    except ImportError:  # pragma: no cover
        return {}
    return {
        "workers": config.get("workers"),
        "max_cron_threads": config.get("max_cron_threads"),
        "limit_memory_soft": config.get("limit_memory_soft"),
        "limit_memory_hard": config.get("limit_memory_hard"),
        "limit_time_cpu": config.get("limit_time_cpu"),
        "limit_time_real": config.get("limit_time_real"),
        "db_maxconn": config.get("db_maxconn"),
    }
