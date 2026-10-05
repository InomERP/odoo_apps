# -*- coding: utf-8 -*-
from odoo import Command
from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged
from odoo.tools import mute_logger


@tagged("post_install", "-at_install")
class TestProductSecondaryUom(TransactionCase):
    """Product configuration, ratios and the Add-line wizard (F-02 to F-05)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.uom_unit = cls.env.ref("uom.product_uom_unit")
        cls.uom_dozen = cls.env.ref("uom.product_uom_dozen")
        cls.uom_kgm = cls.env.ref("uom.product_uom_kgm")

    def _product(self, **vals):
        vals.setdefault("name", "Multi UoM Product")
        vals.setdefault("uom_id", self.uom_unit.id)
        return self.env["product.template"].create(vals)

    # F-02 ---------------------------------------------------------------
    def test_need_secondary_uom_default_false(self):
        self.assertFalse(self._product().need_secondary_uom)

    def test_need_secondary_uom_can_be_enabled(self):
        self.assertTrue(self._product(need_secondary_uom=True).need_secondary_uom)

    # F-04 ---------------------------------------------------------------
    def test_ratio_storage_and_retrieval(self):
        product = self._product(
            need_secondary_uom=True,
            secondary_uom_ids=[
                Command.create({"uom_id": self.uom_dozen.id, "ratio": 12.0}),
            ],
        )
        self.assertEqual(len(product.secondary_uom_ids), 1)
        line = product.secondary_uom_ids
        self.assertEqual(line.uom_id, self.uom_dozen)
        self.assertEqual(line.ratio, 12.0)
        self.assertEqual(line.product_tmpl_id, product)

    def test_ratio_display(self):
        product = self._product(
            need_secondary_uom=True,
            secondary_uom_ids=[
                Command.create({"uom_id": self.uom_dozen.id, "ratio": 12.0}),
            ],
        )
        self.assertEqual(
            product.secondary_uom_ids.ratio_display,
            "1 %s = 12.0 %s" % (self.uom_dozen.name, self.uom_unit.name),
        )

    @mute_logger("odoo.sql_db")
    def test_ratio_must_be_positive(self):
        product = self._product()
        for ratio in (-1.0, 0.0):
            with self.assertRaises(Exception):
                self.env["product.secondary.uom"].create({
                    "product_tmpl_id": product.id,
                    "uom_id": self.uom_dozen.id,
                    "ratio": ratio,
                })

    # F-05 ---------------------------------------------------------------
    def test_multiple_secondary_uoms(self):
        product = self._product(need_secondary_uom=True)
        product.write({"secondary_uom_ids": [
            Command.create({"uom_id": self.uom_dozen.id, "ratio": 12.0}),
            Command.create({"uom_id": self.uom_kgm.id, "ratio": 0.5}),
        ]})
        self.assertEqual(len(product.secondary_uom_ids), 2)
        self.assertEqual(
            sorted(product.secondary_uom_ids.mapped("ratio")), [0.5, 12.0],
        )

    def test_cross_category_uom_allowed(self):
        product = self._product(need_secondary_uom=True)
        line = self.env["product.secondary.uom"].create({
            "product_tmpl_id": product.id,
            "uom_id": self.uom_kgm.id,
            "ratio": 0.5,
        })
        self.assertEqual(line.uom_id, self.uom_kgm)

    # F-04 wizard --------------------------------------------------------
    def test_open_wizard_action(self):
        product = self._product(need_secondary_uom=True)
        action = product.action_open_secondary_uom_wizard()
        self.assertEqual(action["res_model"], "secondary.uom.wizard")
        self.assertEqual(action["target"], "new")
        self.assertEqual(action["context"]["default_product_tmpl_id"], product.id)

    def test_wizard_creates_secondary_uom_line(self):
        product = self._product(need_secondary_uom=True)
        wizard = self.env["secondary.uom.wizard"].create({
            "product_tmpl_id": product.id,
            "uom_id": self.uom_dozen.id,
            "ratio": 12.0,
        })
        result = wizard.action_save_close()
        self.assertEqual(result["type"], "ir.actions.act_window_close")
        self.assertEqual(len(product.secondary_uom_ids), 1)
        self.assertEqual(product.secondary_uom_ids.ratio, 12.0)

    def test_wizard_save_and_new_reopens_wizard(self):
        product = self._product(need_secondary_uom=True)
        wizard = self.env["secondary.uom.wizard"].create({
            "product_tmpl_id": product.id,
            "uom_id": self.uom_dozen.id,
            "ratio": 12.0,
        })
        result = wizard.action_save_new()
        self.assertEqual(result["res_model"], "secondary.uom.wizard")
        self.assertEqual(result["context"]["default_product_tmpl_id"], product.id)
        self.assertEqual(len(product.secondary_uom_ids), 1)

    def test_wizard_rejects_duplicate_uom(self):
        product = self._product(
            need_secondary_uom=True,
            secondary_uom_ids=[
                Command.create({"uom_id": self.uom_dozen.id, "ratio": 12.0}),
            ],
        )
        wizard = self.env["secondary.uom.wizard"].create({
            "product_tmpl_id": product.id,
            "uom_id": self.uom_dozen.id,
            "ratio": 12.0,
        })
        with self.assertRaises(UserError):
            wizard.action_save_close()

    def test_wizard_rejects_non_positive_ratio(self):
        product = self._product(need_secondary_uom=True)
        with self.assertRaises(UserError):
            self.env["secondary.uom.wizard"].create({
                "product_tmpl_id": product.id,
                "uom_id": self.uom_dozen.id,
                "ratio": 0.0,
            })
