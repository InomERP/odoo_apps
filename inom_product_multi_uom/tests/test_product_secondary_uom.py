# -*- coding: utf-8 -*-
from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestProductSecondaryUom(TransactionCase):
    """Phase 2 tests — F-02, F-03, F-04, F-05."""

    def setUp(self):
        super().setUp()
        self.uom_unit = self.env.ref("uom.product_uom_unit")
        self.uom_dozen = self.env.ref("uom.product_uom_dozen")
        self.uom_kgm = self.env.ref("uom.product_uom_kgm")

    # ------------------------------------------------------------------
    # F-02: need_secondary_uom toggle
    # ------------------------------------------------------------------
    def test_need_secondary_uom_default_false(self):
        """need_secondary_uom defaults to False on a new product (F-02)."""
        product = self.env["product.template"].create({"name": "Plain Product"})
        self.assertFalse(product.need_secondary_uom)

    def test_need_secondary_uom_can_be_enabled(self):
        """need_secondary_uom can be set to True (F-02)."""
        product = self.env["product.template"].create({
            "name": "Multi UoM Product",
            "need_secondary_uom": True,
        })
        self.assertTrue(product.need_secondary_uom)

    # ------------------------------------------------------------------
    # F-03: base_uom_id display
    # ------------------------------------------------------------------
    def test_base_uom_id_reflects_uom_id(self):
        """base_uom_id is a related read of the product's base uom_id (F-03)."""
        product = self.env["product.template"].create({
            "name": "Base UoM Product",
            "uom_id": self.uom_kgm.id,
        })
        self.assertEqual(product.base_uom_id, self.uom_kgm)

    # ------------------------------------------------------------------
    # F-04: ratio storage and retrieval
    # ------------------------------------------------------------------
    def test_ratio_storage_and_retrieval(self):
        """A secondary UoM line keeps the uom and ratio it was created with (F-04)."""
        product = self.env["product.template"].create({
            "name": "Test Multi UoM Product",
            "need_secondary_uom": True,
            "secondary_uom_ids": [
                (0, 0, {"uom_id": self.uom_dozen.id, "ratio": 12.0}),
            ],
        })
        self.assertEqual(len(product.secondary_uom_ids), 1)
        line = product.secondary_uom_ids[0]
        self.assertEqual(line.uom_id, self.uom_dozen)
        self.assertEqual(line.ratio, 12.0)
        self.assertEqual(line.product_tmpl_id, product)

    def test_ratio_must_be_positive(self):
        """SQL constraint rejects ratio <= 0 (F-04)."""
        with self.assertRaises(Exception):
            self.env["product.secondary.uom"].create({
                "product_tmpl_id": self.env["product.template"].create(
                    {"name": "Bad Ratio Product"}
                ).id,
                "uom_id": self.uom_unit.id,
                "ratio": -1.0,
            })

    # ------------------------------------------------------------------
    # F-05: unlimited secondary UoMs, including cross-category
    # ------------------------------------------------------------------
    def test_multiple_secondary_uoms(self):
        """Multiple secondary UoM lines can be added per product (F-05)."""
        product = self.env["product.template"].create({"name": "Bulk Rice"})
        product.write({
            "need_secondary_uom": True,
            "secondary_uom_ids": [
                (0, 0, {"uom_id": self.uom_unit.id, "ratio": 1.0}),
                (0, 0, {"uom_id": self.uom_dozen.id, "ratio": 12.0}),
            ],
        })
        self.assertEqual(len(product.secondary_uom_ids), 2)
        self.assertEqual(
            sorted(product.secondary_uom_ids.mapped("ratio")), [1.0, 12.0]
        )

    def test_cross_category_uom_allowed(self):
        """Secondary UoMs from different categories are allowed (F-05)."""
        product = self.env["product.template"].create({
            "name": "Cross Category Product",
            "uom_id": self.uom_unit.id,
            "need_secondary_uom": True,
        })
        # kg is a different category from unit — must be allowed
        line = self.env["product.secondary.uom"].create({
            "product_tmpl_id": product.id,
            "uom_id": self.uom_kgm.id,
            "ratio": 0.5,
        })
        self.assertEqual(line.uom_id, self.uom_kgm)

    # ------------------------------------------------------------------
    # F-04 wizard: duplicate UoM validation
    # ------------------------------------------------------------------
    def test_wizard_rejects_duplicate_uom(self):
        """Wizard raises UserError when the same UoM is added twice (F-04)."""
        product = self.env["product.template"].create({
            "name": "Dup Test Product",
            "need_secondary_uom": True,
            "secondary_uom_ids": [
                (0, 0, {"uom_id": self.uom_dozen.id, "ratio": 12.0}),
            ],
        })
        wizard = self.env["secondary.uom.wizard"].create({
            "product_tmpl_id": product.id,
            "uom_id": self.uom_dozen.id,
            "ratio": 12.0,
        })
        with self.assertRaises(UserError):
            wizard.action_add_secondary_uom()

    def test_wizard_creates_secondary_uom_line(self):
        """Wizard creates a new product.secondary.uom line on save (F-04)."""
        product = self.env["product.template"].create({
            "name": "Wizard Test Product",
            "need_secondary_uom": True,
        })
        wizard = self.env["secondary.uom.wizard"].create({
            "product_tmpl_id": product.id,
            "uom_id": self.uom_dozen.id,
            "ratio": 12.0,
        })
        wizard.action_add_secondary_uom()
        self.assertEqual(len(product.secondary_uom_ids), 1)
        self.assertEqual(product.secondary_uom_ids[0].ratio, 12.0)
