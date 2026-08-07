# -*- coding: utf-8 -*-
"""Probes.

These run the real statements against the real cursor. That matters most for
the Odoo-layer queries: they now pass their window as a bind parameter rather
than formatting it into the statement, and a parameterised query that is
never executed in a test is a parameterised query nobody has checked.
"""

from odoo.tests.common import TransactionCase, tagged

from ..tools import host, odoo_stats, postgres
from ..tools.collector import collect


@tagged("post_install", "-at_install")
class TestServerHealthProbes(TransactionCase):

    # ---- Odoo layer ------------------------------------------------------

    def test_crons_probe_runs(self):
        self.env.flush_all()
        result = odoo_stats.crons(self.env.cr)
        for key in ("active_count", "late_count", "failing_count"):
            self.assertIsInstance(result[key], int)
        self.assertIsInstance(result["late"], list)

    def test_crons_probe_finds_a_late_job(self):
        """Exercises the second statement, the one listing late rows."""
        cron = self.env["ir.cron"].search([], limit=1)
        self.assertTrue(cron, "base always ships scheduled actions")
        cron.write({"active": True})
        self.env.flush_all()
        self.env.cr.execute(
            "UPDATE ir_cron SET nextcall = (now() at time zone 'UTC') "
            "- interval '1 hour' WHERE id = %s", (cron.id,))
        self.env.invalidate_all()

        result = odoo_stats.crons(self.env.cr, late_after_minutes=1)
        self.assertGreaterEqual(result["late_count"], 1)
        self.assertTrue(result["late"])
        self.assertIn("behind_s", result["late"][0])
        self.assertGreater(result["late"][0]["behind_s"], 0)

    def test_cron_window_is_applied_not_ignored(self):
        """A wide window must not report the same backlog as a narrow one."""
        cron = self.env["ir.cron"].search([], limit=1)
        cron.write({"active": True})
        self.env.flush_all()
        self.env.cr.execute(
            "UPDATE ir_cron SET nextcall = (now() at time zone 'UTC') "
            "- interval '10 minutes' WHERE id = %s", (cron.id,))
        self.env.invalidate_all()

        narrow = odoo_stats.crons(self.env.cr, late_after_minutes=1)
        wide = odoo_stats.crons(self.env.cr, late_after_minutes=600)
        self.assertGreater(narrow["late_count"], wide["late_count"])

    def test_cron_window_rejects_a_non_numeric_value(self):
        """The window is cast before it can reach the statement."""
        with self.assertRaises(ValueError):
            odoo_stats.crons(self.env.cr, late_after_minutes="1; DROP TABLE")

    def test_mail_queue_probe_runs(self):
        self.env.flush_all()
        result = odoo_stats.mail_queue(self.env.cr)
        self.assertIsInstance(result["outgoing"], int)
        self.assertIsInstance(result["failed"], int)

    def test_active_users_probe_runs(self):
        result = odoo_stats.active_users(self.env.cr)
        self.assertIn("available", result)
        if result["available"]:
            self.assertIsInstance(result["online"], int)
            self.assertIsInstance(result["recent"], int)
            self.assertIsInstance(result["rows"], list)

    def test_active_users_window_rejects_a_non_numeric_value(self):
        with self.assertRaises(ValueError):
            odoo_stats.active_users(self.env.cr, active_window_minutes="x")

    def test_config_limits_shape(self):
        limits = odoo_stats.config_limits()
        for key in ("workers", "limit_memory_hard", "db_maxconn"):
            self.assertIn(key, limits)

    def test_worker_enumeration_shape(self):
        result = odoo_stats.workers()
        self.assertIn("available", result)
        self.assertIsInstance(result["items"], list)

    # ---- PostgreSQL ------------------------------------------------------

    def test_postgres_live_probe_runs(self):
        result = postgres.live(self.env.cr)
        self.assertIsInstance(result, dict)

    def test_database_size_probe_runs(self):
        self.assertGreater(postgres.database_size(self.env.cr) or 0, 0)

    # ---- host ------------------------------------------------------------

    def test_cpu_allowance_is_memoised_and_sane(self):
        cores, physical, capped = host.cpu_allowance()
        self.assertGreater(cores, 0)
        self.assertGreater(physical, 0)
        self.assertIsInstance(capped, bool)
        self.assertEqual(host.cpu_allowance(), (cores, physical, capped))

    def test_memory_probe_shape(self):
        mem = host.memory()
        self.assertIn("percent", mem)
        self.assertGreaterEqual(mem.get("percent") or 0, 0)

    def test_load_average_shape(self):
        load = host.load_average()
        self.assertIn("1m", load)

    # ---- end to end ------------------------------------------------------

    def test_collect_returns_every_block(self):
        payload = collect(self.env.cr)
        for key in ("ts", "host", "postgres", "odoo", "collect_ms",
                    "capabilities"):
            self.assertIn(key, payload)
        self.assertIn("crons", payload["odoo"])
        self.assertIn("mail", payload["odoo"])
        self.assertIn("limits", payload["odoo"])
        self.assertGreaterEqual(payload["collect_ms"], 0)

    def test_collected_payload_feeds_the_sample_model(self):
        """The probe output and the column mapping must stay in step."""
        payload = collect(self.env.cr)
        Sample = self.env["inom.server.health.sample"]
        vals = Sample._sample_values(payload)
        self.assertFalse(set(vals) - set(Sample._fields))
        self.assertTrue(Sample.create(vals).id)
