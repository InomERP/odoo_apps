# -*- coding: utf-8 -*-
from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestSecondaryUomValidation(TransactionCase):
    """F-12: secondary UoM validation rules."""

    def setUp(self):
        super().setUp()
        self.uom = self.env["uom.uom"].search([], limit=1)
        self.product = self.env["product.template"].create(
            {"name": "Validation Test Product", "need_secondary_uom": True}
        )

    def test_duplicate_secondary_uom_rejected(self):
        """The same UoM cannot be added twice for one product."""
        self.env["product.secondary.uom"].create(
            {"product_tmpl_id": self.product.id, "uom_id": self.uom.id, "ratio": 5.0}
        )
        with self.assertRaises(ValidationError):
            self.env["product.secondary.uom"].create(
                {"product_tmpl_id": self.product.id, "uom_id": self.uom.id, "ratio": 7.0}
            )

    def test_secondary_uom_equals_base_rejected(self):
        """A secondary UoM identical to the product's base UoM is rejected."""
        base_uom = self.product.uom_id
        if not base_uom:
            self.skipTest("Product has no base UoM in this database.")
        with self.assertRaises(ValidationError):
            self.env["product.secondary.uom"].create(
                {
                    "product_tmpl_id": self.product.id,
                    "uom_id": base_uom.id,
                    "ratio": 1.0,
                }
            )
