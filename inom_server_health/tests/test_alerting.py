# -*- coding: utf-8 -*-
"""Alert rule evaluation.

The behaviour worth protecting is the debounce/cooldown pair: a rule must not
fire on a single spike, and must not keep firing for the same open incident.
Both are easy to break during a refactor and neither shows up in a manual
click-through, so they are pinned here.
"""

from datetime import timedelta

from odoo import fields
from odoo.exceptions import AccessError
from odoo.tests import new_test_user
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestServerHealthAlerting(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Rule = cls.env["inom.server.health.rule"]
        cls.Alert = cls.env["inom.server.health.alert"]
        cls.Sample = cls.env["inom.server.health.sample"]
        # The module ships starter rules. Park them so each test evaluates
        # only the rules it created and the assertions stay exact.
        cls.Rule.search([("active", "=", True)]).write({"active": False})

    def _rule(self, **overrides):
        vals = {
            "name": "Test rule",
            "metric": "cpu_percent",
            "operator": ">=",
            "threshold": 80.0,
            "consecutive_breaches": 3,
            "cooldown_minutes": 60,
            "severity": "warning",
            "notify_email": False,
        }
        vals.update(overrides)
        return self.Rule.create(vals)

    def _sample(self, **values):
        vals = {"sampled_at": fields.Datetime.now(), "node": "test-node"}
        vals.update(values)
        return self.Sample.create(vals)

    # ---- debounce --------------------------------------------------------

    def test_single_spike_opens_no_alert(self):
        rule = self._rule(consecutive_breaches=3)
        self.Rule._evaluate(self._sample(cpu_percent=99.0))
        self.assertEqual(rule.breach_streak, 1)
        self.assertFalse(self.Alert.search([("rule_id", "=", rule.id)]))

    def test_alert_opens_on_the_nth_consecutive_breach(self):
        rule = self._rule(consecutive_breaches=3)
        for _index in range(2):
            self.Rule._evaluate(self._sample(cpu_percent=99.0))
        self.assertFalse(self.Alert.search([("rule_id", "=", rule.id)]))

        self.Rule._evaluate(self._sample(cpu_percent=99.0))
        alert = self.Alert.search([("rule_id", "=", rule.id)])
        self.assertEqual(len(alert), 1)
        self.assertEqual(alert.state, "open")
        self.assertEqual(alert.trigger_value, 99.0)
        self.assertEqual(alert.node, "test-node")
        self.assertTrue(rule.last_notified_at)

    def test_one_clean_sample_resets_the_streak(self):
        rule = self._rule(consecutive_breaches=3)
        self.Rule._evaluate(self._sample(cpu_percent=99.0))
        self.Rule._evaluate(self._sample(cpu_percent=99.0))
        self.assertEqual(rule.breach_streak, 2)

        self.Rule._evaluate(self._sample(cpu_percent=10.0))
        self.assertEqual(rule.breach_streak, 0)

        # Debounce restarts from scratch, so two more breaches still open
        # nothing.
        self.Rule._evaluate(self._sample(cpu_percent=99.0))
        self.Rule._evaluate(self._sample(cpu_percent=99.0))
        self.assertFalse(self.Alert.search([("rule_id", "=", rule.id)]))

    # ---- recovery --------------------------------------------------------

    def test_recovery_resolves_the_open_alert(self):
        rule = self._rule(consecutive_breaches=1)
        self.Rule._evaluate(self._sample(cpu_percent=99.0))
        alert = self.Alert.search([("rule_id", "=", rule.id)])
        self.assertEqual(alert.state, "open")

        self.Rule._evaluate(self._sample(cpu_percent=5.0))
        self.assertEqual(alert.state, "resolved")
        self.assertEqual(alert.last_value, 5.0)
        self.assertTrue(alert.resolved_at)
        self.assertEqual(rule.breach_streak, 0)

    def test_recovery_then_breach_opens_a_second_alert(self):
        rule = self._rule(consecutive_breaches=1)
        self.Rule._evaluate(self._sample(cpu_percent=99.0))
        self.Rule._evaluate(self._sample(cpu_percent=5.0))
        self.Rule._evaluate(self._sample(cpu_percent=99.0))
        alerts = self.Alert.search([("rule_id", "=", rule.id)])
        self.assertEqual(len(alerts), 2)
        self.assertEqual(len(alerts.filtered(lambda a: a.state == "open")), 1)

    # ---- cooldown --------------------------------------------------------

    def test_cooldown_suppresses_repeat_notification(self):
        rule = self._rule(consecutive_breaches=1, cooldown_minutes=60)
        self.Rule._evaluate(self._sample(cpu_percent=99.0))
        first = rule.last_notified_at
        self.assertTrue(first)

        self.Rule._evaluate(self._sample(cpu_percent=99.0))
        self.assertEqual(rule.last_notified_at, first,
                         "cooldown must not be re-stamped while quiet")

    def test_expired_cooldown_notifies_again(self):
        rule = self._rule(consecutive_breaches=1, cooldown_minutes=60)
        self.Rule._evaluate(self._sample(cpu_percent=99.0))
        rule.last_notified_at = fields.Datetime.now() - timedelta(minutes=120)

        self.Rule._evaluate(self._sample(cpu_percent=99.0))
        self.assertGreater(rule.last_notified_at,
                           fields.Datetime.now() - timedelta(minutes=1))

    # ---- value tracking --------------------------------------------------

    def test_peak_climbs_for_an_upper_bound_rule(self):
        rule = self._rule(consecutive_breaches=1, operator=">=", threshold=80.0)
        self.Rule._evaluate(self._sample(cpu_percent=85.0))
        alert = self.Alert.search([("rule_id", "=", rule.id)])
        self.Rule._evaluate(self._sample(cpu_percent=97.0))
        self.Rule._evaluate(self._sample(cpu_percent=90.0))
        self.assertEqual(alert.peak_value, 97.0)
        self.assertEqual(alert.last_value, 90.0)

    def test_peak_falls_for_a_lower_bound_rule(self):
        rule = self._rule(consecutive_breaches=1, operator="<=",
                          metric="pg_cache_hit_pct", threshold=95.0)
        self.Rule._evaluate(self._sample(pg_cache_hit_pct=90.0))
        alert = self.Alert.search([("rule_id", "=", rule.id)])
        self.Rule._evaluate(self._sample(pg_cache_hit_pct=70.0))
        self.Rule._evaluate(self._sample(pg_cache_hit_pct=80.0))
        self.assertEqual(alert.peak_value, 70.0)
        self.assertEqual(alert.last_value, 80.0)

    # ---- batching --------------------------------------------------------

    def test_many_rules_in_one_pass(self):
        """Every rule is still decided independently after batching."""
        breaching = self._rule(name="cpu high", consecutive_breaches=1,
                               metric="cpu_percent", threshold=80.0)
        quiet = self._rule(name="disk high", consecutive_breaches=1,
                           metric="disk_percent", threshold=90.0)
        slow = self._rule(name="mem high", consecutive_breaches=5,
                          metric="memory_percent", threshold=50.0)

        self.Rule._evaluate(self._sample(cpu_percent=99.0, disk_percent=1.0,
                                         memory_percent=88.0))

        self.assertEqual(len(self.Alert.search([("rule_id", "=", breaching.id)])), 1)
        self.assertFalse(self.Alert.search([("rule_id", "=", quiet.id)]))
        self.assertFalse(self.Alert.search([("rule_id", "=", slow.id)]))
        self.assertEqual(breaching.breach_streak, 1)
        self.assertEqual(quiet.breach_streak, 0)
        self.assertEqual(slow.breach_streak, 1)

    def test_rules_sharing_a_streak_are_written_together(self):
        first = self._rule(name="a", consecutive_breaches=9, threshold=80.0)
        second = self._rule(name="b", consecutive_breaches=9, threshold=70.0)
        self.Rule._evaluate(self._sample(cpu_percent=99.0))
        self.Rule._evaluate(self._sample(cpu_percent=99.0))
        self.assertEqual(first.breach_streak, 2)
        self.assertEqual(second.breach_streak, 2)

    def test_open_alert_count_matches(self):
        rule = self._rule(consecutive_breaches=1)
        self.Rule._evaluate(self._sample(cpu_percent=99.0))
        self.assertEqual(rule.open_alert_count, 1)
        self.Rule._evaluate(self._sample(cpu_percent=1.0))
        self.assertEqual(rule.open_alert_count, 0)

    def test_evaluation_with_no_active_rules_is_a_no_op(self):
        self.Rule.search([("active", "=", True)]).write({"active": False})
        self.Rule._evaluate(self._sample(cpu_percent=99.0))
        self.assertFalse(self.Alert.search(
            [("state", "in", ["open", "resolved"])]))

    def test_inactive_rule_is_not_evaluated(self):
        rule = self._rule(consecutive_breaches=1, active=False)
        self.Rule._evaluate(self._sample(cpu_percent=99.0))
        self.assertFalse(self.Alert.search([("rule_id", "=", rule.id)]))

    # ---- description -----------------------------------------------------

    def test_alert_describes_itself_both_ways(self):
        rule = self._rule(consecutive_breaches=1)
        self.Rule._evaluate(self._sample(cpu_percent=99.0))
        alert = self.Alert.search([("rule_id", "=", rule.id)])
        self.assertIn("CPU %", alert._describe())
        self.assertIn("test-node", alert._describe())
        self.assertIn("Recovered", alert._describe(resolved=True))

    def test_duration_is_positive_while_open(self):
        rule = self._rule(consecutive_breaches=1)
        self.Rule._evaluate(self._sample(cpu_percent=99.0))
        alert = self.Alert.search([("rule_id", "=", rule.id)])
        alert.opened_at = fields.Datetime.now() - timedelta(hours=2)
        alert.invalidate_recordset(["duration_s"])
        self.assertGreater(alert.duration_s, 1.5)

    # ---- access ----------------------------------------------------------

    def test_viewer_can_read_but_not_change_rules(self):
        viewer = new_test_user(
            self.env, login="health_viewer_test",
            groups="inom_server_health.group_server_health_viewer")
        rule = self._rule()
        rule.with_user(viewer).read(["name"])
        with self.assertRaises(AccessError):
            self.Rule.with_user(viewer).create({
                "name": "nope", "metric": "cpu_percent", "threshold": 1.0})

    def test_manager_can_maintain_rules(self):
        manager = new_test_user(
            self.env, login="health_manager_test",
            groups="inom_server_health.group_server_health_manager")
        rule = self.Rule.with_user(manager).create({
            "name": "manager rule", "metric": "cpu_percent",
            "threshold": 50.0, "notify_email": False})
        rule.with_user(manager).write({"threshold": 60.0})
        self.assertEqual(rule.threshold, 60.0)
