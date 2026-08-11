# -*- coding: utf-8 -*-
# Part of INOM Smart Credit Limit. See LICENSE file for full copyright and licensing details.

from datetime import timedelta

from odoo import fields
from odoo.exceptions import UserError, ValidationError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged('post_install', '-at_install')
class TestSmartCreditLimit(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # The running user must be a credit manager to exercise overrides.
        cls.env.ref('inom_smart_credit_limit.group_smart_credit_manager') \
            .sudo().user_ids = [(4, cls.env.user.id)]
        cls.company = cls.env.company
        cls.partner = cls.env['res.partner'].create({
            'name': 'INOM Test Customer',
            'is_company': True,
            'use_smart_credit': True,
            'smart_credit_limit': 1000.0,
        })
        # A service product keeps the tests free of stock and tax noise.
        cls.product = cls.env['product.product'].create({
            'name': 'INOM Test Service',
            'type': 'service',
            'list_price': 100.0,
            'taxes_id': [(5, 0, 0)],
        })

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _create_order(self, amount, partner=None):
        return self.env['sale.order'].create({
            'partner_id': (partner or self.partner).id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_uom_qty': 1,
                'price_unit': amount,
                'tax_id': [(5, 0, 0)],
            })],
        })

    def _refresh(self, record=None):
        (record or self.partner).invalidate_recordset()

    # ------------------------------------------------------------------
    # Exposure and availability
    # ------------------------------------------------------------------
    def test_initial_position_is_the_full_limit(self):
        self.assertEqual(self.partner.smart_credit_exposure, 0.0)
        self.assertEqual(self.partner.smart_available_credit, 1000.0)
        self.assertEqual(self.partner.smart_extra_credit, 0.0)
        self.assertEqual(self.partner.smart_credit_utilization, 0.0)

    def test_confirmed_order_increases_exposure(self):
        order = self._create_order(400.0)
        self.assertTrue(order.action_confirm())
        self.assertEqual(order.state, 'sale')
        self._refresh()
        self.assertEqual(self.partner.smart_credit_exposure, 400.0)
        self.assertEqual(self.partner.smart_available_credit, 600.0)

    def test_disabled_partner_is_not_controlled(self):
        other = self.env['res.partner'].create({'name': 'INOM Uncontrolled'})
        order = self._create_order(50000.0, partner=other)
        self.assertEqual(order.credit_state, 'none')
        self.assertTrue(order.action_confirm())
        self.assertEqual(order.state, 'sale')

    # ------------------------------------------------------------------
    # Blocking and override
    # ------------------------------------------------------------------
    def test_order_within_limit_confirms(self):
        order = self._create_order(500.0)
        self.assertEqual(order.credit_state, 'ok')
        self.assertTrue(order.action_confirm())
        self.assertEqual(order.state, 'sale')

    def test_order_over_limit_is_blocked(self):
        order = self._create_order(2000.0)
        self.assertEqual(order.credit_state, 'blocked')
        action = order.action_confirm()
        self.assertIsInstance(action, dict)
        self.assertEqual(action.get('res_model'),
                         'inom.credit.check.wizard')
        self.assertEqual(order.state, 'draft')
        self.assertTrue(self.env['inom.credit.audit'].search([
            ('partner_id', '=', self.partner.id), ('event', '=', 'block')]))

    def test_override_requires_a_reason(self):
        order = self._create_order(2000.0)
        action = order.action_confirm()
        wizard = self.env['inom.credit.check.wizard'].browse(
            action['res_id'])
        with self.assertRaises(UserError):
            wizard.action_override_confirm()
        self.assertEqual(order.state, 'draft')

    def test_override_with_reason_confirms_and_is_audited(self):
        order = self._create_order(2000.0)
        action = order.action_confirm()
        wizard = self.env['inom.credit.check.wizard'].browse(
            action['res_id'])
        wizard.override_reason = 'Cheque received'
        wizard.action_override_confirm()
        self.assertEqual(order.state, 'sale')
        self.assertTrue(order.credit_override)
        self.assertEqual(order.credit_state, 'approved')
        self.assertTrue(self.env['inom.credit.audit'].search([
            ('partner_id', '=', self.partner.id),
            ('event', '=', 'override')]))

    def test_approval_request_flags_the_order(self):
        order = self._create_order(2000.0)
        action = order.action_confirm()
        wizard = self.env['inom.credit.check.wizard'].browse(
            action['res_id'])
        wizard.action_request_approval()
        self.assertTrue(order.credit_approval_requested)
        self.assertEqual(order.state, 'draft')
        self.assertTrue(self.env['inom.credit.audit'].search([
            ('partner_id', '=', self.partner.id),
            ('event', '=', 'approval_request')]))

    def test_warn_mode_lets_the_order_through(self):
        self.partner.credit_enforcement = 'warn'
        order = self._create_order(2000.0)
        self.assertEqual(order.credit_state, 'warn')
        self.assertTrue(order.action_confirm())
        self.assertEqual(order.state, 'sale')

    # ------------------------------------------------------------------
    # Credit hold
    # ------------------------------------------------------------------
    def test_manual_hold_blocks_and_release_restores(self):
        self.partner.action_credit_hold()
        self.assertTrue(self.partner.is_credit_hold)
        self.assertEqual(self.partner.credit_hold_source, 'manual')
        order = self._create_order(10.0)
        self.assertEqual(order.credit_state, 'hold')
        action = order.action_confirm()
        self.assertIsInstance(action, dict)
        self.assertEqual(order.state, 'draft')

        self.partner.action_credit_release()
        self.assertFalse(self.partner.is_credit_hold)
        self._refresh(order)
        self.assertTrue(order.action_confirm())
        self.assertEqual(order.state, 'sale')

    # ------------------------------------------------------------------
    # Temporary extensions
    # ------------------------------------------------------------------
    def test_active_extension_raises_available_credit(self):
        today = fields.Date.context_today(self.partner)
        extension = self.env['inom.credit.extension'].create({
            'name': 'Festive season',
            'partner_id': self.partner.id,
            'amount': 500.0,
            'date_start': today,
            'date_end': today + timedelta(days=30),
        })
        self._refresh()
        self.assertEqual(self.partner.smart_extra_credit, 500.0)
        self.assertEqual(self.partner.smart_available_credit, 1500.0)

        extension.action_cancel()
        self._refresh()
        self.assertEqual(extension.state, 'cancelled')
        self.assertEqual(self.partner.smart_extra_credit, 0.0)

    def test_extension_dates_are_validated(self):
        today = fields.Date.context_today(self.partner)
        with self.assertRaises(ValidationError):
            self.env['inom.credit.extension'].create({
                'name': 'Wrong dates',
                'partner_id': self.partner.id,
                'amount': 100.0,
                'date_start': today,
                'date_end': today - timedelta(days=1),
            })

    def test_extension_amount_must_be_positive(self):
        today = fields.Date.context_today(self.partner)
        with self.assertRaises(ValidationError):
            self.env['inom.credit.extension'].create({
                'name': 'Zero amount',
                'partner_id': self.partner.id,
                'amount': 0.0,
                'date_start': today,
                'date_end': today + timedelta(days=1),
            })

    def test_expired_extension_stops_counting(self):
        today = fields.Date.context_today(self.partner)
        extension = self.env['inom.credit.extension'].create({
            'name': 'Past extension',
            'partner_id': self.partner.id,
            'amount': 500.0,
            'date_start': today - timedelta(days=10),
            'date_end': today - timedelta(days=1),
        })
        self._refresh()
        self.assertEqual(self.partner.smart_extra_credit, 0.0)
        self.env['res.partner']._inom_expire_extensions(today)
        self.assertEqual(extension.state, 'expired')

    # ------------------------------------------------------------------
    # Scoring and policy resolution
    # ------------------------------------------------------------------
    def test_new_customer_gets_the_neutral_score(self):
        self.assertEqual(self.partner.smart_credit_score, 70)
        self.assertEqual(self.partner.smart_suggested_limit, 0.0)

    def test_suggested_limit_follows_the_score(self):
        self.assertEqual(self.partner._inom_suggested_limit(90), 1300.0)
        self.assertEqual(self.partner._inom_suggested_limit(75), 1000.0)
        self.assertEqual(self.partner._inom_suggested_limit(60), 900.0)
        self.assertEqual(self.partner._inom_suggested_limit(20), 800.0)

    def test_apply_suggested_limit_writes_and_audits(self):
        self.partner.invalidate_recordset()
        limit = self.partner.smart_credit_limit
        self.partner.action_apply_suggested_limit()
        # Without history there is no suggestion, so nothing changes.
        self.assertEqual(self.partner.smart_credit_limit, limit)

    def test_partner_enforcement_overrides_global_policy(self):
        self.partner.credit_enforcement = 'block'
        self.assertEqual(self.partner._inom_resolve_action('warn'), 'block')
        self.partner.credit_enforcement = 'follow'
        self.assertEqual(self.partner._inom_resolve_action('warn'), 'warn')
        self.assertEqual(self.partner._inom_resolve_action('off'), 'ok')

    def test_audit_counter_matches_the_log(self):
        self.partner.action_credit_hold()
        self.partner.action_credit_release()
        self._refresh()
        self.assertEqual(
            self.partner.credit_audit_count,
            self.env['inom.credit.audit'].search_count(
                [('partner_id', '=', self.partner.id)]))
