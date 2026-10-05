# -*- coding: utf-8 -*-
from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestSecondaryUomValidation(TransactionCase):
    """F-12: secondary UoM validation rules."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.uom_unit = cls.env.ref("uom.product_uom_unit")
        cls.uom_dozen = cls.env.ref("uom.product_uom_dozen")
        cls.product = cls.env["product.template"].create({
            "name": "Validation Test Product",
            "uom_id": cls.uom_unit.id,
            "need_secondary_uom": True,
        })

    def test_duplicate_secondary_uom_rejected(self):
        """The same UoM cannot be added twice for one product."""
        self.env["product.secondary.uom"].create({
            "product_tmpl_id": self.product.id,
            "uom_id": self.uom_dozen.id,
            "ratio": 12.0,
        })
        with self.assertRaises(ValidationError):
            self.env["product.secondary.uom"].create({
                "product_tmpl_id": self.product.id,
                "uom_id": self.uom_dozen.id,
                "ratio": 6.0,
            })

    def test_secondary_uom_equals_base_rejected(self):
        """A secondary UoM identical to the product's base UoM is rejected."""
        with self.assertRaises(ValidationError):
            self.env["product.secondary.uom"].create({
                "product_tmpl_id": self.product.id,
                "uom_id": self.uom_unit.id,
                "ratio": 1.0,
            })

    def test_same_uom_allowed_on_different_products(self):
        other = self.env["product.template"].create({
            "name": "Other Product", "uom_id": self.uom_unit.id,
        })
        for product in (self.product, other):
            self.env["product.secondary.uom"].create({
                "product_tmpl_id": product.id,
                "uom_id": self.uom_dozen.id,
                "ratio": 12.0,
            })
        self.assertEqual(self.product.secondary_uom_ids.uom_id, self.uom_dozen)
        self.assertEqual(other.secondary_uom_ids.uom_id, self.uom_dozen)
