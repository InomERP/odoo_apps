# -*- coding: utf-8 -*-

from psycopg2 import IntegrityError

from odoo.exceptions import AccessError
from odoo.fields import Command
from odoo.tests import TransactionCase, tagged
from odoo.tools import mute_logger

from odoo.addons.inom_multi_company_email_signatures import post_init_hook

IMG = 'data:image/png;base64,iVBORw0KGgo='


@tagged('post_install', '-at_install')
class TestMultiCompanySignature(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_a = cls.env['res.company'].create({'name': 'Signature Co A'})
        cls.company_b = cls.env['res.company'].create({'name': 'Signature Co B'})
        group_user = cls.env.ref('base.group_user')
        cls.user = cls.env['res.users'].create({
            'name': 'Signature User',
            'login': 'signature_user',
            'company_id': cls.company_a.id,
            'company_ids': [Command.set((cls.company_a | cls.company_b).ids)],
            'group_ids': [Command.set(group_user.ids)],
        })
        cls.other_user = cls.env['res.users'].create({
            'name': 'Other Signature User',
            'login': 'other_signature_user',
            'company_id': cls.company_a.id,
            'company_ids': [Command.set(cls.company_a.ids)],
            'group_ids': [Command.set(group_user.ids)],
        })
        cls.admin = cls.env['res.users'].create({
            'name': 'Signature Admin',
            'login': 'signature_admin',
            'company_id': cls.company_a.id,
            'company_ids': [Command.set((cls.company_a | cls.company_b).ids)],
            'group_ids': [Command.set(cls.env.ref('base.group_system').ids)],
        })
        cls.Sig = cls.env['res.users.signature']
        cls.other_sig = cls.Sig.create({
            'user_id': cls.other_user.id,
            'company_id': cls.company_a.id,
            'signature': '<p>Other</p>',
        })

    def _signature_in(self, user, company, as_user=None):
        env_user = (as_user or user)
        allowed = [company.id] + [c.id for c in env_user.company_ids if c != company]
        record = user.with_user(env_user).with_context(allowed_company_ids=allowed)
        record.invalidate_recordset(['signature'])
        return record.signature

    # ------------------------------------------------------------------
    # Security
    # ------------------------------------------------------------------

    def test_groups_implied(self):
        self.assertTrue(self.user.has_group(
            'inom_multi_company_email_signatures.group_signature_user'))
        self.assertFalse(self.user.has_group(
            'inom_multi_company_email_signatures.group_signature_manager'))
        self.assertTrue(self.admin.has_group(
            'inom_multi_company_email_signatures.group_signature_manager'))

    def test_unique_user_company(self):
        self.Sig.create({
            'user_id': self.user.id,
            'company_id': self.company_a.id,
            'signature': 'first',
        })
        with mute_logger('odoo.sql_db'), self.assertRaises(IntegrityError), self.cr.savepoint():
            self.Sig.create({
                'user_id': self.user.id,
                'company_id': self.company_a.id,
                'signature': 'second',
            })
            self.env.flush_all()

    def test_user_sees_only_own_signatures(self):
        own = self.Sig.create({
            'user_id': self.user.id,
            'company_id': self.company_b.id,
            'signature': 'mine',
        })
        # The domain matches both users' rows: only the access rule can hide other_sig
        visible = self.Sig.with_user(self.user).search([
            ('user_id', 'in', (self.user | self.other_user).ids),
        ])
        self.assertEqual(visible, own)
        with self.assertRaises(AccessError):
            self.other_sig.with_user(self.user).read(['signature'])
        with self.assertRaises(AccessError):
            self.Sig.with_user(self.user).create({
                'user_id': self.other_user.id,
                'company_id': self.company_b.id,
                'signature': 'forged',
            })

    def test_admin_sees_all_signatures(self):
        self.assertIn(self.other_sig, self.Sig.with_user(self.admin).search([
            ('user_id', '=', self.other_user.id),
        ]))
        self.other_sig.with_user(self.admin).signature = 'changed by admin'
        self.assertEqual(self.other_sig.signature, 'changed by admin')

    def test_user_cannot_edit_other_user(self):
        with self.assertRaises(AccessError):
            self.other_user.with_user(self.user).write({'signature_ids': [
                Command.create({'company_id': self.company_a.id, 'signature': 'x'}),
            ]})
        self.assertTrue(self.other_sig.exists())
        self.assertEqual(self.other_sig.signature, '<p>Other</p>')

    def test_user_cannot_escalate_privileges(self):
        with self.assertRaises(AccessError):
            self.user.with_user(self.user).write({
                'group_ids': [Command.link(self.env.ref('base.group_system').id)],
            })

    # ------------------------------------------------------------------
    # Business logic
    # ------------------------------------------------------------------

    def test_profile_write_creates_and_replaces(self):
        me = self.user.with_user(self.user)
        me.write({'signature_ids': [
            Command.create({'company_id': self.company_a.id, 'signature': 'draw:' + IMG}),
            Command.create({'company_id': self.company_b.id, 'signature': '<p>B</p>'}),
            Command.create({'company_id': self.company_b.id, 'signature': ''}),  # ignored
        ]})
        self.assertEqual(len(self.user.signature_ids), 2)

        me.write({'signature_ids': [
            Command.create({'company_id': self.company_a.id, 'signature': 'typed:' + IMG}),
        ]})
        sig_a = self.user.signature_ids.filtered(lambda s: s.company_id == self.company_a)
        self.assertEqual(len(sig_a), 1)
        self.assertEqual(sig_a.signature, 'typed:' + IMG)
        self.assertEqual(len(self.user.signature_ids), 2)

    def test_compute_follows_active_company(self):
        self.Sig.create([
            {'user_id': self.user.id, 'company_id': self.company_a.id, 'signature': 'upload:' + IMG},
            {'user_id': self.user.id, 'company_id': self.company_b.id, 'signature': '<p>Text B</p>'},
        ])
        sig_a = self._signature_in(self.user, self.company_a)
        self.assertIn('<img', sig_a)
        self.assertIn(IMG, sig_a)
        self.assertNotIn('upload:', sig_a)
        self.assertEqual(self._signature_in(self.user, self.company_b), '<p>Text B</p>')

    def test_compute_falls_back_to_default_company(self):
        self.Sig.create({
            'user_id': self.other_user.id,
            'company_id': self.company_b.id,
            'signature': 'unused',
        })
        # Admin works in company B, which other_user does not belong to
        signature = self._signature_in(self.other_user, self.company_b, as_user=self.admin)
        self.assertEqual(signature, '<p>Other</p>')

    def test_compute_empty(self):
        self.assertFalse(self._signature_in(self.user, self.company_a))

    def test_inverse_writes_active_company(self):
        me_b = self.user.with_user(self.user).with_context(
            allowed_company_ids=[self.company_b.id, self.company_a.id])
        me_b.signature = '<p>Set in B</p>'
        self.env.flush_all()
        sig = self.user.signature_ids
        self.assertEqual(sig.company_id, self.company_b)
        self.assertEqual(sig.signature, '<p>Set in B</p>')

        me_b.signature = '<p>Updated in B</p>'
        self.env.flush_all()
        self.assertEqual(self.user.signature_ids, sig)
        self.assertEqual(sig.signature, '<p>Updated in B</p>')

    def test_inverse_batch(self):
        users = (self.user | self.other_user).with_context(
            allowed_company_ids=[self.company_a.id])
        users.write({'signature': '<p>Batch</p>'})
        for user in self.user | self.other_user:
            sig = user.signature_ids.filtered(lambda s: s.company_id == self.company_a)
            self.assertEqual(sig.signature, '<p>Batch</p>')

    def test_post_init_hook_migrates_raw_signatures(self):
        self.Sig.search([('user_id', '=', self.user.id)]).unlink()
        self.env.flush_all()
        self.env.cr.execute(
            "UPDATE res_users SET signature = %s WHERE id = %s",
            ('<p>Legacy</p>', self.user.id),
        )
        self.env.cr.execute(
            "UPDATE res_users SET signature = %s WHERE id = %s",
            ('<p>Legacy other</p>', self.other_user.id),
        )
        post_init_hook(self.env)

        sig = self.Sig.search([('user_id', '=', self.user.id)])
        self.assertEqual(sig.company_id, self.company_a)
        self.assertEqual(sig.signature, '<p>Legacy</p>')
        self.other_sig.invalidate_recordset()
        self.assertEqual(self.other_sig.signature, '<p>Legacy other</p>')
