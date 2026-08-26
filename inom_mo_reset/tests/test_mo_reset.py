# -*- coding: utf-8 -*-
# Part of inom_mo_reset. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.exceptions import AccessError, UserError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged('post_install', '-at_install')
class TestMoReset(TransactionCase):
    """Workflow, data-integrity and security tests for inom_mo_reset."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Production = cls.env['mrp.production']

        # A manufactured product with a stockable component + a 1-operation BoM.
        cls.component = cls.env['product.product'].create({
            'name': 'INOM Component',
            'is_storable': True,
        })
        cls.finished = cls.env['product.product'].create({
            'name': 'INOM Finished',
            'is_storable': True,
        })
        cls.workcenter = cls.env['mrp.workcenter'].create({
            'name': 'INOM Workcenter',
        })
        cls.bom = cls.env['mrp.bom'].create({
            'product_tmpl_id': cls.finished.product_tmpl_id.id,
            'product_qty': 1.0,
            'type': 'normal',
            'bom_line_ids': [Command.create({
                'product_id': cls.component.id,
                'product_qty': 3.0,
            })],
            'operation_ids': [Command.create({
                'name': 'Cutting',
                'workcenter_id': cls.workcenter.id,
            })],
        })

        # Reset-capable user (manufacturing user + reset group).
        cls.reset_user = cls.env['res.users'].create({
            'name': 'Reset User',
            'login': 'inom_reset_user',
            'groups_id': [Command.link(
                cls.env.ref('inom_mo_reset.group_mo_reset_user').id)],
        })
        # Plain manufacturing user WITHOUT the reset group.
        cls.plain_user = cls.env['res.users'].create({
            'name': 'Plain MRP User',
            'login': 'inom_plain_user',
            'groups_id': [Command.link(cls.env.ref('mrp.group_mrp_user').id)],
        })

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------
    def _new_confirmed_mo(self, qty=50.0):
        mo = self.Production.create({
            'product_id': self.finished.id,
            'bom_id': self.bom.id,
            'product_qty': qty,
        })
        mo.action_confirm()
        return mo

    # ------------------------------------------------------------------
    # F1 / F3 - core reset transition
    # ------------------------------------------------------------------
    def test_reset_cancelled_mo_to_draft(self):
        mo = self._new_confirmed_mo()
        mo.action_cancel()
        self.assertEqual(mo.state, 'cancel')

        mo.with_user(self.reset_user).action_set_to_draft()
        self.assertEqual(mo.state, 'draft',
                         "Cancelled MO must return to draft after reset.")

    # ------------------------------------------------------------------
    # F4 / F6 / F7 - data preservation
    # ------------------------------------------------------------------
    def test_data_is_preserved(self):
        mo = self._new_confirmed_mo(qty=50.0)
        original = {
            'product': mo.product_id,
            'bom': mo.bom_id,
            'qty': mo.product_qty,
            'date_start': mo.date_start,
        }
        mo.action_cancel()
        mo.with_user(self.reset_user).action_set_to_draft()

        self.assertEqual(mo.product_id, original['product'])
        self.assertEqual(mo.bom_id, original['bom'])
        self.assertEqual(mo.product_qty, original['qty'])
        self.assertEqual(mo.date_start, original['date_start'])

        # F7 - fields editable again in draft.
        mo.product_qty = 75.0
        self.assertEqual(mo.product_qty, 75.0)

    # ------------------------------------------------------------------
    # F5 - raw material moves revived to draft
    # ------------------------------------------------------------------
    def test_raw_moves_reset_to_draft(self):
        mo = self._new_confirmed_mo()
        self.assertTrue(mo.move_raw_ids)
        mo.action_cancel()
        self.assertTrue(all(m.state == 'cancel' for m in mo.move_raw_ids))

        mo.with_user(self.reset_user).action_set_to_draft()
        self.assertTrue(
            all(m.state == 'draft' for m in mo.move_raw_ids),
            "All raw material moves must be reset to draft.")
        self.assertFalse(any(m.picked for m in mo.move_raw_ids))

    # ------------------------------------------------------------------
    # F8 - work orders restored to ready ("To Do")
    # ------------------------------------------------------------------
    def test_workorders_restored(self):
        mo = self._new_confirmed_mo()
        self.assertTrue(mo.workorder_ids)
        mo.action_cancel()
        self.assertTrue(all(w.state == 'cancel' for w in mo.workorder_ids))

        mo.with_user(self.reset_user).action_set_to_draft()
        self.assertTrue(
            all(w.state == 'ready' for w in mo.workorder_ids),
            "All work orders must be revived to the 'ready' state.")

    # ------------------------------------------------------------------
    # F9 / F10 - flag lifecycle
    # ------------------------------------------------------------------
    def test_flag_lifecycle(self):
        mo = self._new_confirmed_mo()
        self.assertFalse(mo.set_to_draft)
        mo.action_cancel()
        mo.with_user(self.reset_user).action_set_to_draft()
        self.assertTrue(mo.set_to_draft, "Flag must be True right after reset.")

        # Re-confirm clears the flag.
        mo.action_confirm()
        self.assertFalse(mo.set_to_draft,
                         "Flag must clear when the MO is re-confirmed.")

    def test_flag_cleared_on_recancel(self):
        mo = self._new_confirmed_mo()
        mo.action_cancel()
        mo.with_user(self.reset_user).action_set_to_draft()
        self.assertTrue(mo.set_to_draft)
        mo.action_cancel()
        self.assertFalse(mo.set_to_draft,
                         "Flag must clear when the MO is cancelled again.")

    # ------------------------------------------------------------------
    # F11 - normal workflow resumes after reset
    # ------------------------------------------------------------------
    def test_post_reset_workflow(self):
        mo = self._new_confirmed_mo()
        mo.action_cancel()
        mo.with_user(self.reset_user).action_set_to_draft()
        self.assertEqual(mo.state, 'draft')

        mo.action_confirm()
        self.assertEqual(mo.state, 'confirmed',
                         "A reset MO must confirm exactly like a fresh order.")

    # ------------------------------------------------------------------
    # F2 - guard: non-cancelled orders cannot be reset
    # ------------------------------------------------------------------
    def test_cannot_reset_non_cancelled(self):
        mo = self._new_confirmed_mo()
        with self.assertRaises(UserError):
            mo.with_user(self.reset_user).action_set_to_draft()

    def test_eligibility_helper(self):
        confirmed = self._new_confirmed_mo()
        cancelled = self._new_confirmed_mo()
        cancelled.action_cancel()
        batch = confirmed | cancelled
        self.assertEqual(batch._inom_can_set_to_draft(), cancelled)

    # ------------------------------------------------------------------
    # Security - user without the group is rejected
    # ------------------------------------------------------------------
    def test_security_blocks_unauthorized_user(self):
        mo = self._new_confirmed_mo()
        mo.action_cancel()
        with self.assertRaises(AccessError):
            mo.with_user(self.plain_user).action_set_to_draft()

    def test_security_blocks_plain_manager(self):
        """A Manufacturing *manager* who was NOT granted the reset group must
        not be able to reset (access is opt-in: admin or explicit grant only)."""
        manager = self.env['res.users'].create({
            'name': 'Plain MRP Manager',
            'login': 'inom_plain_manager',
            'groups_id': [Command.link(self.env.ref('mrp.group_mrp_manager').id)],
        })
        self.assertFalse(
            manager.has_group('inom_mo_reset.group_mo_reset_user'),
            "A plain manufacturing manager must NOT auto-receive the reset group.")
        self.assertFalse(manager.has_group('base.group_system'))
        mo = self._new_confirmed_mo()
        mo.action_cancel()
        with self.assertRaises(AccessError):
            mo.with_user(manager).action_set_to_draft()

    def test_system_admin_can_reset_without_reset_group(self):
        """The System administrator can reset even without the reset group
        explicitly assigned (case 1 of the two allowed cases)."""
        admin_like = self.env['res.users'].create({
            'name': 'System Admin No Reset Group',
            'login': 'inom_sysadmin',
            'groups_id': [
                Command.link(self.env.ref('base.group_system').id),
                Command.link(self.env.ref('mrp.group_mrp_manager').id),
            ],
        })
        self.assertFalse(
            admin_like.has_group('inom_mo_reset.group_mo_reset_user'),
            "Test precondition: admin must not hold the reset group here.")
        mo = self._new_confirmed_mo()
        mo.action_cancel()
        mo.with_user(admin_like).action_set_to_draft()
        self.assertEqual(mo.state, 'draft')

    # ------------------------------------------------------------------
    # F12 - batch / multi-record reset (concurrency-shaped path)
    # ------------------------------------------------------------------
    def test_batch_reset(self):
        mos = self.Production
        for _i in range(3):
            mo = self._new_confirmed_mo()
            mo.action_cancel()
            mos |= mo
        mos.with_user(self.reset_user).action_set_to_draft()
        self.assertTrue(all(m.state == 'draft' for m in mos))
        self.assertTrue(all(m.set_to_draft for m in mos))
