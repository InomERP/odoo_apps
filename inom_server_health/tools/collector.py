# -*- coding: utf-8 -*-
"""Assembles the live payload.

Design rule: the live endpoint performs ZERO writes and ZERO ORM traversals.
Everything is a raw cursor read or a /proc read, each behind its own TTL. The
result is measured; if collection exceeds BUDGET_MS we log a warning and the
UI surfaces the cost so a slow instance is visible rather than silent.
"""

import logging
import time

from .cache import CACHE
from . import host, odoo_stats, postgres

_logger = logging.getLogger(__name__)

# Per-metric freshness. Polling faster than these just serves cache.
TTL = {
    "host": 1.0,
    "disk": 30.0,
    "pg_live": 2.0,
    "pg_size": 60.0,
    "pg_caps": 300.0,
    "crons": 15.0,
    "mail": 30.0,
    "workers": 5.0,
    "users": 15.0,
    "config": 300.0,
}

BUDGET_MS = 150.0


def _data_dir():
    try:
        from odoo.tools import config
        return config.filestore("") or config.get("data_dir")
    except Exception:
        return None


def collect(cr):
    started = time.monotonic()

    limits = CACHE.get_or_set("config", TTL["config"],
                              odoo_stats.config_limits, default={})

    payload = {
        "ts": int(time.time()),
        "host": {
            "cpu_percent": host.cpu_percent(),
            "cpu_allowance": CACHE.get_or_set(
                "cpu_alw", TTL["config"], host.cpu_allowance),
            "memory": CACHE.get_or_set("host", TTL["host"], host.memory),
            "load": host.load_average(),
            "uptime_s": CACHE.get_or_set(
                "uptime", TTL["disk"], host.uptime_seconds),
            "disks": CACHE.get_or_set(
                "disk", TTL["disk"],
                lambda: host.disk([_data_dir(), "/"]), default=[]),
        },
        "postgres": CACHE.get_or_set(
            "pg_live", TTL["pg_live"], lambda: postgres.live(cr), default={}),
        "odoo": {
            "crons": CACHE.get_or_set(
                "crons", TTL["crons"], lambda: odoo_stats.crons(cr), default={}),
            "mail": CACHE.get_or_set(
                "mail", TTL["mail"], lambda: odoo_stats.mail_queue(cr), default={}),
            "users": CACHE.get_or_set(
                "users", TTL["users"],
                lambda: odoo_stats.active_users(cr), default={}),
            "workers": CACHE.get_or_set(
                "workers", TTL["workers"],
                lambda: odoo_stats.workers(limits.get("limit_memory_hard")),
                default={"available": False, "items": []}),
            "limits": limits,
        },
    }

    payload["postgres"]["db_size"] = CACHE.get_or_set(
        "pg_size", TTL["pg_size"], lambda: postgres.database_size(cr))

    caps = CACHE.get_or_set("pg_caps", TTL["pg_caps"], lambda: {
        "pg_monitor": postgres.has_pg_monitor(cr),
        "pg_stat_statements": postgres.has_statements_extension(cr),
    }, default={})
    payload["capabilities"] = caps

    elapsed_ms = round((time.monotonic() - started) * 1000, 1)
    payload["collect_ms"] = elapsed_ms
    if elapsed_ms > BUDGET_MS:
        _logger.warning(
            "Server health collection took %.1f ms (budget %.0f ms). "
            "Raise the TTLs or the poll interval.", elapsed_ms, BUDGET_MS)
    return payload
