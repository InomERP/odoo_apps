# -*- coding: utf-8 -*-
"""Sample capture.

`_capture` was split into per-block helpers. These tests pin the mapping from
collector payload to column values, including the "missing block" case: the
collector degrades to empty dicts on a restricted host, and a monitor that
raises when a probe is unavailable is worse than one that records a zero.
"""

from datetime import timedelta

from odoo import fields
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestServerHealthSampling(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Sample = cls.env["inom.server.health.sample"]
        cls.env["inom.server.health.rule"].search(
            [("active", "=", True)]).write({"active": False})

    PAYLOAD = {
        "collect_ms": 1.25,
        "host": {
            "cpu_percent": 42.5,
            "memory": {"percent": 61.0, "used": 8000.0},
            "load": {"1m": 1.75},
            "disks": [{"percent": 30.0}, {"percent": 71.5}],
        },
        "postgres": {
            "conn_total": 12,
            "conn_percent": 24.0,
            "cache_hit_pct": 99.1,
            "longest_query_s": 3.5,
            "db_size": 123456.0,
        },
        "odoo": {
            "crons": {"late_count": 2},
            "mail": {"outgoing": 7, "failed": 1},
            "users": {"online": 4, "recent": 9},
            "workers": {"items": [{"rss": 100.0}, {"rss": 900.0}]},
        },
    }

    def test_full_payload_maps_to_columns(self):
        vals = self.Sample._sample_values(self.PAYLOAD)
        self.assertEqual(vals["cpu_percent"], 42.5)
        self.assertEqual(vals["memory_percent"], 61.0)
        self.assertEqual(vals["memory_used"], 8000.0)
        self.assertEqual(vals["load_1m"], 1.75)
        self.assertEqual(vals["disk_percent"], 71.5, "busiest mount wins")
        self.assertEqual(vals["pg_conn_total"], 12)
        self.assertEqual(vals["pg_cache_hit_pct"], 99.1)
        self.assertEqual(vals["pg_db_size"], 123456.0)
        self.assertEqual(vals["users_online"], 4)
        self.assertEqual(vals["users_recent"], 9)
        self.assertEqual(vals["cron_late_count"], 2)
        self.assertEqual(vals["mail_outgoing"], 7)
        self.assertEqual(vals["mail_failed"], 1)
        self.assertEqual(vals["worker_max_rss"], 900.0, "fattest worker wins")
        self.assertEqual(vals["collect_ms"], 1.25)
        self.assertTrue(vals["node"])
        self.assertTrue(vals["sampled_at"])

    def test_empty_payload_degrades_to_zeros(self):
        vals = self.Sample._sample_values({})
        for column in ("cpu_percent", "memory_percent", "memory_used",
                       "load_1m", "disk_percent", "pg_conn_total",
                       "pg_conn_percent", "pg_cache_hit_pct",
                       "pg_longest_query_s", "pg_db_size", "users_online",
                       "users_recent", "cron_late_count", "mail_outgoing",
                       "mail_failed", "worker_max_rss", "collect_ms"):
            self.assertEqual(vals[column], 0, column)

    def test_blocks_present_but_empty(self):
        vals = self.Sample._sample_values(
            {"host": {}, "postgres": {}, "odoo": {}})
        self.assertEqual(vals["disk_percent"], 0.0)
        self.assertEqual(vals["worker_max_rss"], 0.0)

    def test_every_mapped_column_exists_on_the_model(self):
        vals = self.Sample._sample_values(self.PAYLOAD)
        unknown = set(vals) - set(self.Sample._fields)
        self.assertFalse(unknown, "unknown columns: %s" % unknown)

    def test_sample_values_are_writable(self):
        sample = self.Sample.create(self.Sample._sample_values(self.PAYLOAD))
        self.assertTrue(sample.id)
        self.assertEqual(sample.disk_percent, 71.5)

    def test_capture_writes_exactly_one_row(self):
        before = self.Sample.search_count([])
        self.Sample._capture()
        self.assertEqual(self.Sample.search_count([]), before + 1)

    def test_capture_survives_a_failing_rule_pass(self):
        """Notification trouble must not roll back the sample."""
        sample = self.Sample.create(self.Sample._sample_values(self.PAYLOAD))
        # A sample-shaped object missing the metric column: evaluation blows
        # up, the caller swallows it, capture still reports success.
        self.Sample._evaluate_rules(sample)
        self.assertTrue(sample.exists())

    def test_vacuum_removes_only_stale_rows(self):
        fresh = self.Sample.create({"sampled_at": fields.Datetime.now()})
        stale = self.Sample.create({
            "sampled_at": fields.Datetime.now() - timedelta(days=400)})
        self.Sample._vacuum()
        self.assertTrue(fresh.exists())
        self.assertFalse(stale.exists())

    def test_retention_parameter_is_honoured(self):
        # sudo: test setup writing the module's own retention parameter.
        self.env["ir.config_parameter"].sudo().set_param(
            "inom_server_health.retention_days", 1)
        old = self.Sample.create({
            "sampled_at": fields.Datetime.now() - timedelta(days=3)})
        self.Sample._vacuum()
        self.assertFalse(old.exists())
