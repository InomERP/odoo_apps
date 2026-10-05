# -*- coding: utf-8 -*-
from odoo import Command
from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestSaleOrderLineSecondaryUom(TransactionCase):
    """Sale order line behaviour (F-06 to F-09, F-11, F-12)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.uom_unit = cls.env.ref("uom.product_uom_unit")
        cls.uom_dozen = cls.env.ref("uom.product_uom_dozen")
        cls.uom_kgm = cls.env.ref("uom.product_uom_kgm")
        cls.partner = cls.env["res.partner"].create({"name": "Multi UoM Customer"})
        cls.multi_product = cls.env["product.template"].create({
            "name": "Multi UoM Product",
            "uom_id": cls.uom_unit.id,
            "list_price": 10.0,
            "need_secondary_uom": True,
            "secondary_uom_ids": [
                Command.create({"uom_id": cls.uom_dozen.id, "ratio": 12.0}),
            ],
        }).product_variant_id
        cls.plain_product = cls.env["product.template"].create({
            "name": "Plain Product",
            "uom_id": cls.uom_unit.id,
            "list_price": 5.0,
        }).product_variant_id

    def _order(self, line_vals):
        return self.env["sale.order"].create({
            "partner_id": self.partner.id,
            "order_line": [Command.create(line_vals)],
        })

    def test_base_quantity_is_secondary_qty_times_ratio(self):
        order = self._order({
            "product_id": self.multi_product.id,
            "secondary_uom_id": self.uom_dozen.id,
            "secondary_qty": 2,
        })
        self.assertEqual(order.order_line.product_uom_qty, 24.0)
        self.assertEqual(order.order_line.secondary_factor, 12.0)

    def test_write_recomputes_base_quantity(self):
        order = self._order({
            "product_id": self.multi_product.id,
            "secondary_uom_id": self.uom_dozen.id,
            "secondary_qty": 2,
        })
        order.order_line.write({"secondary_qty": 3})
        self.assertEqual(order.order_line.product_uom_qty, 36.0)

    def test_secondary_uom_defaults_to_first_secondary(self):
        order = self._order({"product_id": self.multi_product.id})
        self.assertEqual(order.order_line.secondary_uom_id, self.uom_dozen)
        # no secondary quantity entered -> base quantity untouched
        self.assertEqual(order.order_line.product_uom_qty, 1.0)

    def test_secondary_uom_defaults_to_base_uom_without_secondary(self):
        order = self._order({"product_id": self.plain_product.id})
        self.assertEqual(order.order_line.secondary_uom_id, self.uom_unit)

    def test_base_uom_as_secondary_leaves_quantity_unchanged(self):
        order = self._order({
            "product_id": self.multi_product.id,
            "product_uom_qty": 5,
            "secondary_uom_id": self.uom_unit.id,
            "secondary_qty": 9,
        })
        self.assertEqual(order.order_line.product_uom_qty, 5.0)

    def test_invalid_secondary_uom_rejected(self):
        with self.assertRaises(ValidationError):
            self._order({
                "product_id": self.multi_product.id,
                "secondary_uom_id": self.uom_kgm.id,
                "secondary_qty": 1,
            })

    def test_conversion_display(self):
        order = self._order({
            "product_id": self.multi_product.id,
            "secondary_uom_id": self.uom_dozen.id,
            "secondary_qty": 2,
        })
        self.assertEqual(
            order.order_line.secondary_conversion_display,
            "2 %s = 24 %s" % (self.uom_dozen.name, self.uom_unit.name),
        )
        self.assertEqual(order.order_line.base_uom_name, self.uom_unit.name)

    def test_allowed_secondary_uoms_include_base_and_secondary(self):
        order = self._order({"product_id": self.multi_product.id})
        self.assertEqual(
            order.order_line.inom_allowed_secondary_uom_ids,
            self.uom_unit | self.uom_dozen,
        )

    def test_invoice_line_carries_secondary_uom(self):
        order = self._order({
            "product_id": self.multi_product.id,
            "secondary_uom_id": self.uom_dozen.id,
            "secondary_qty": 2,
        })
        values = order.order_line._prepare_invoice_line()
        self.assertEqual(values["secondary_uom_id"], self.uom_dozen.id)
        self.assertEqual(values["secondary_qty"], 2.0)

    def test_invoice_line_without_real_secondary_uom(self):
        order = self._order({"product_id": self.plain_product.id})
        values = order.order_line._prepare_invoice_line()
        self.assertNotIn("secondary_uom_id", values)
