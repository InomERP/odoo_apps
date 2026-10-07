from odoo import Command
from odoo.exceptions import AccessError, ValidationError
from odoo.tests import HttpCase, TransactionCase, new_test_user, tagged


@tagged("post_install", "-at_install")
class TestReadonlyUser(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.group = cls.env.ref("inom_readonly_user.group_users_readonly")
        cls.partner = cls.env["res.partner"].create({"name": "Test Partner"})
        cls.ro_user = new_test_user(
            cls.env, login="ro_user", groups="base.group_user,base.group_partner_manager"
        )
        cls.ro_user.group_ids = [Command.link(cls.group.id)]
        cls.normal_user = new_test_user(
            cls.env, login="normal_user", groups="base.group_user,base.group_partner_manager"
        )

    def test_readonly_user_can_read(self):
        partner = self.partner.with_user(self.ro_user)
        self.assertEqual(partner.name, "Test Partner")
        self.assertTrue(partner.has_access("read"))
        self.assertTrue(self.env["res.partner"].with_user(self.ro_user).search([]))

    def test_readonly_user_cannot_modify(self):
        Partner = self.env["res.partner"].with_user(self.ro_user)
        partner = self.partner.with_user(self.ro_user)
        with self.assertRaises(AccessError):
            partner.write({"name": "Changed"})
        with self.assertRaises(AccessError):
            Partner.create({"name": "New"})
        with self.assertRaises(AccessError):
            partner.unlink()
        self.assertFalse(Partner.has_access("create"))
        self.assertFalse(partner.has_access("write"))

    def test_sudo_still_works(self):
        partner = self.partner.with_user(self.ro_user).sudo()
        partner.write({"name": "Sudo Changed"})
        self.assertEqual(self.partner.name, "Sudo Changed")

    def test_normal_user_unaffected(self):
        partner = self.partner.with_user(self.normal_user)
        partner.write({"name": "Normal Changed"})
        self.env["res.partner"].with_user(self.normal_user).create({"name": "X"})

    def test_admin_cannot_make_self_readonly(self):
        admin = self.env.ref("base.user_admin")
        with self.assertRaises(ValidationError):
            admin.with_user(admin).write({"group_ids": [Command.link(self.group.id)]})

    def test_admin_can_edit_self_and_others(self):
        admin = self.env.ref("base.user_admin")
        admin.with_user(admin).write({"name": "Admin %s" % self.group.id})
        self.normal_user.with_user(admin).write({"group_ids": [Command.link(self.group.id)]})
        self.assertTrue(self.normal_user._has_group("inom_readonly_user.group_users_readonly"))


@tagged("post_install", "-at_install")
class TestReadonlyUserLogin(HttpCase):
    def test_readonly_user_can_login(self):
        user = new_test_user(self.env, login="ro_login", password="ro_login_pwd", groups="base.group_user")
        user.group_ids = [Command.link(self.env.ref("inom_readonly_user.group_users_readonly").id)]
        self.authenticate("ro_login", "ro_login_pwd")
        res = self.url_open("/odoo")
        self.assertEqual(res.status_code, 200)
