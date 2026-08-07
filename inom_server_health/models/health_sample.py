# -*- coding: utf-8 -*-
"""History samples.

The live endpoint never writes. All persistence happens here, on a cron, so
the write rate is fixed at one row per interval regardless of how many admins
have the dashboard open.
"""

import logging
import socket
from datetime import timedelta

from odoo import api, fields, models
from odoo.tools import config

from ..tools.collector import collect

_logger = logging.getLogger(__name__)


class ServerHealthSample(models.Model):
    _name = "inom.server.health.sample"
    _description = "Server Health Sample"
    _order = "sampled_at desc"
    _rec_name = "sampled_at"

    sampled_at = fields.Datetime(required=True, index=True,
                                 default=fields.Datetime.now)
    node = fields.Char(index=True, help="Hostname this sample came from.")

    cpu_percent = fields.Float(group_operator="avg")
    memory_percent = fields.Float(group_operator="avg")
    memory_used = fields.Float(help="Bytes.")
    load_1m = fields.Float(group_operator="avg")
    disk_percent = fields.Float(group_operator="avg")

    pg_conn_total = fields.Integer()
    pg_conn_percent = fields.Float(group_operator="avg")
    pg_cache_hit_pct = fields.Float(group_operator="avg")
    pg_longest_query_s = fields.Float(group_operator="avg")
    pg_db_size = fields.Float(help="Bytes.")

    users_online = fields.Integer(help="Users with an active session.")
    users_recent = fields.Integer(
        help="Users seen in the last 30 minutes, online or not.")
    cron_late_count = fields.Integer()
    mail_outgoing = fields.Integer()
    mail_failed = fields.Integer()
    worker_max_rss = fields.Float(help="Bytes.")

    collect_ms = fields.Float(help="Cost of the probe itself.")

    @api.model
    def _capture(self):
        """Cron entry point. One row, one flush.

        Kept to the three things that actually happen -- probe, write,
        evaluate -- with the payload flattening in its own helpers. The
        column values produced are identical to the single-block version;
        only the shape of the code changed.
        """
        payload = collect(self.env.cr)
        sample = self.create(self._sample_values(payload))
        self._evaluate_rules(sample)
        return True

    @api.model
    def _sample_values(self, payload):
        """Flatten one collector payload into one row of column values."""
        vals = {
            "sampled_at": fields.Datetime.now(),
            "node": socket.gethostname(),
            "collect_ms": payload.get("collect_ms") or 0.0,
        }
        vals.update(self._host_values(payload.get("host") or {}))
        vals.update(self._postgres_values(payload.get("postgres") or {}))
        vals.update(self._odoo_values(payload.get("odoo") or {}))
        return vals

    @api.model
    def _host_values(self, host_block):
        """CPU, memory, load and the busiest mount point."""
        mem = host_block.get("memory") or {}
        disks = host_block.get("disks") or []
        load = host_block.get("load") or {}
        return {
            "cpu_percent": host_block.get("cpu_percent") or 0.0,
            "memory_percent": mem.get("percent") or 0.0,
            "memory_used": mem.get("used") or 0.0,
            "load_1m": load.get("1m") or 0.0,
            "disk_percent": max([d["percent"] for d in disks], default=0.0),
        }

    @api.model
    def _postgres_values(self, pg_block):
        """Connection pressure, cache hit ratio and database size."""
        return {
            "pg_conn_total": pg_block.get("conn_total") or 0,
            "pg_conn_percent": pg_block.get("conn_percent") or 0.0,
            "pg_cache_hit_pct": pg_block.get("cache_hit_pct") or 0.0,
            "pg_longest_query_s": pg_block.get("longest_query_s") or 0.0,
            "pg_db_size": pg_block.get("db_size") or 0.0,
        }

    @api.model
    def _odoo_values(self, odoo_block):
        """Concurrency, cron backlog, mail queue and the fattest worker."""
        crons = odoo_block.get("crons") or {}
        mail = odoo_block.get("mail") or {}
        users = odoo_block.get("users") or {}
        workers = (odoo_block.get("workers") or {}).get("items") or []
        return {
            "users_online": users.get("online") or 0,
            "users_recent": users.get("recent") or 0,
            "cron_late_count": crons.get("late_count") or 0,
            "mail_outgoing": mail.get("outgoing") or 0,
            "mail_failed": mail.get("failed") or 0,
            "worker_max_rss": max([w["rss"] for w in workers], default=0.0),
        }

    @api.model
    def _evaluate_rules(self, sample):
        """Evaluate alert rules against the row we just wrote.

        No extra probes and no extra host queries -- it reuses this sample.
        A failing notification channel must never roll back the sample that
        triggered it, so the whole pass is wrapped.
        """
        try:
            self.env["inom.server.health.rule"]._evaluate(sample)
        except Exception:
            _logger.exception("Server health: alert evaluation failed")

    @api.model
    def _vacuum(self):
        """Keep the table bounded. A monitor that fills the disk is a bug."""
        # sudo: ir.config_parameter is readable only by Settings users, and
        # this runs as the cron user. It reads one own-namespace key and
        # returns an integer, so no record data is exposed.
        days = int(self.env["ir.config_parameter"].sudo().get_param(
            "inom_server_health.retention_days", 30))
        cutoff = fields.Datetime.now() - timedelta(days=days)
        stale = self.search([("sampled_at", "<", cutoff)], limit=20000)
        if stale:
            _logger.info("Vacuuming %s server health samples", len(stale))
            stale.unlink()
        return True
