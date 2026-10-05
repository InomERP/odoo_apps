# -*- coding: utf-8 -*-
"""PostgreSQL probes.

Cost budget: the live probe is ONE round trip. Every additional query is a
network hop plus a share of the request's transaction time, and this runs on a
timer forever.

Explicitly excluded from the live path:
  * pg_stat_user_tables scans and bloat estimation -- these touch every
    relation and are O(number of tables). Odoo databases have thousands.
  * pg_database_size -- stats every file in the data directory. Cached 60 s.
  * pg_total_relation_size loops -- cron only.
"""

import logging

_logger = logging.getLogger(__name__)

LIVE_SQL = """
SELECT
    (SELECT count(*) FROM pg_stat_activity
      WHERE datname = current_database())                         AS conn_total,
    (SELECT count(*) FROM pg_stat_activity
      WHERE datname = current_database() AND state = 'active')    AS conn_active,
    (SELECT count(*) FROM pg_stat_activity
      WHERE datname = current_database()
        AND state = 'idle in transaction')                        AS conn_idle_tx,
    current_setting('max_connections')::int                       AS conn_max,
    (SELECT COALESCE(EXTRACT(EPOCH FROM max(now() - query_start)), 0)
       FROM pg_stat_activity
      WHERE datname = current_database()
        AND state = 'active'
        AND query_start IS NOT NULL
        AND pid <> pg_backend_pid())                              AS longest_query_s,
    (SELECT COALESCE(EXTRACT(EPOCH FROM max(now() - xact_start)), 0)
       FROM pg_stat_activity
      WHERE datname = current_database()
        AND state = 'idle in transaction'
        AND xact_start IS NOT NULL)                               AS longest_idle_tx_s,
    (SELECT COALESCE(round(100.0 * sum(blks_hit)
        / NULLIF(sum(blks_hit) + sum(blks_read), 0), 2), 0)
       FROM pg_stat_database WHERE datname = current_database())  AS cache_hit_pct,
    (SELECT COALESCE(sum(deadlocks), 0)
       FROM pg_stat_database WHERE datname = current_database())  AS deadlocks,
    (SELECT COALESCE(sum(temp_bytes), 0)
       FROM pg_stat_database WHERE datname = current_database())  AS temp_bytes
"""


def live(cr):
    """Single round trip. Typical cost: 1-3 ms.

    Note on permissions: without the pg_monitor role, pg_stat_activity only
    exposes rows for the connecting user. Odoo owns all its own sessions, so
    the connection counts stay correct -- but any non-Odoo session (a psql
    shell, a BI tool, a replica) is invisible. Grant pg_monitor for full
    visibility; the module degrades quietly without it.
    """
    cr.execute(LIVE_SQL)
    row = cr.dictfetchone() or {}
    conn_max = row.get("conn_max") or 0
    conn_total = row.get("conn_total") or 0
    return {
        "conn_total": conn_total,
        "conn_active": row.get("conn_active") or 0,
        "conn_idle_tx": row.get("conn_idle_tx") or 0,
        "conn_max": conn_max,
        "conn_percent": round(100.0 * conn_total / conn_max, 1) if conn_max else None,
        "longest_query_s": round(float(row.get("longest_query_s") or 0), 1),
        "longest_idle_tx_s": round(float(row.get("longest_idle_tx_s") or 0), 1),
        "cache_hit_pct": float(row.get("cache_hit_pct") or 0),
        "deadlocks": row.get("deadlocks") or 0,
        "temp_bytes": row.get("temp_bytes") or 0,
    }


def database_size(cr):
    """Cached 60 s by the caller -- pg_database_size stats the data dir."""
    cr.execute("SELECT pg_database_size(current_database())")
    row = cr.fetchone()
    return row[0] if row else None


def has_pg_monitor(cr):
    try:
        cr.execute("SELECT pg_has_role(current_user, 'pg_monitor', 'member')")
        row = cr.fetchone()
        return bool(row and row[0])
    except Exception:
        return False


def has_statements_extension(cr):
    try:
        cr.execute(
            "SELECT 1 FROM pg_extension WHERE extname = 'pg_stat_statements'")
        return bool(cr.fetchone())
    except Exception:
        return False


def slowest_statements(cr, limit=10):
    """Cron-only. Requires pg_stat_statements in shared_preload_libraries,
    which needs a postgresql.conf edit and a server restart -- Odoo cannot
    enable it. Returns [] when unavailable.
    """
    if not has_statements_extension(cr):
        return []
    try:
        cr.execute("""
            SELECT calls, round(mean_exec_time::numeric, 2) AS mean_ms,
                   round(total_exec_time::numeric, 2) AS total_ms,
                   left(query, 300) AS query
              FROM pg_stat_statements s
              JOIN pg_database d ON d.oid = s.dbid
             WHERE d.datname = current_database()
             ORDER BY total_exec_time DESC
             LIMIT %s
        """, (limit,))
        return cr.dictfetchall()
    except Exception:
        _logger.debug("pg_stat_statements unavailable", exc_info=True)
        return []
