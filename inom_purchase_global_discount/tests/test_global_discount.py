from odoo import Command
from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestPurchaseGlobalDiscount(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.vendor = cls.env['res.partner'].create({'name': 'Discount Vendor'})
        cls.product_a = cls.env['product.product'].create({'name': 'PGD Product A'})
        cls.product_b = cls.env['product.product'].create({'name': 'PGD Product B'})
        # total = 2 * 100 + 1 * 300 = 500
        cls.order = cls.env['purchase.order'].create({
            'partner_id': cls.vendor.id,
            'order_line': [
                Command.create({
                    'product_id': cls.product_a.id,
                    'product_qty': 2,
                    'price_unit': 100,
                }),
                Command.create({
                    'product_id': cls.product_b.id,
                    'product_qty': 1,
                    'price_unit': 300,
                }),
            ],
        })

    def test_no_discount_type_leaves_lines_untouched(self):
        self.assertEqual(self.order.global_discount_amount, 0.0)
        self.assertEqual(self.order.order_line.mapped('discount'), [0.0, 0.0])

    def test_percent_discount(self):
        self.order.write({'discount_type': 'percent', 'discount_rate': 10})
        self.assertAlmostEqual(self.order.global_discount_amount, 50.0)
        for line in self.order.order_line:
            self.assertAlmostEqual(line.discount, 10.0)

    def test_percent_discount_follows_rate_change(self):
        self.order.write({'discount_type': 'percent', 'discount_rate': 10})
        self.order.write({'discount_rate': 20})
        self.assertAlmostEqual(self.order.global_discount_amount, 100.0)
        for line in self.order.order_line:
            self.assertAlmostEqual(line.discount, 20.0)

    def test_amount_discount_is_spread_proportionally(self):
        self.order.write({'discount_type': 'amount', 'discount_rate': 50})
        self.assertAlmostEqual(self.order.global_discount_amount, 50.0)
        # 50 over a 500 total -> 10% on each line
        for line in self.order.order_line:
            self.assertAlmostEqual(line.discount, 10.0, places=3)

    def test_discount_applied_on_create(self):
        order = self.env['purchase.order'].create({
            'partner_id': self.vendor.id,
            'discount_type': 'percent',
            'discount_rate': 5,
            'order_line': [Command.create({
                'product_id': self.product_a.id,
                'product_qty': 4,
                'price_unit': 50,
            })],
        })
        self.assertAlmostEqual(order.order_line.discount, 5.0)
        self.assertAlmostEqual(order.global_discount_amount, 10.0)

    def test_section_lines_get_no_discount(self):
        self.order.write({
            'order_line': [Command.create({
                'display_type': 'line_section',
                'name': 'Section',
            })],
        })
        self.order.write({'discount_type': 'percent', 'discount_rate': 10})
        section = self.order.order_line.filtered('display_type')
        self.assertEqual(section.discount, 0.0)

    def test_max_percent_limit(self):
        self.env['ir.config_parameter'].set_float(
            'purchase_global_discount.max_discount_limit', 15.0,
        )
        with self.assertRaises(ValidationError):
            self.order.write({'discount_type': 'percent', 'discount_rate': 16})
        self.order.write({'discount_type': 'percent', 'discount_rate': 15})
        self.assertAlmostEqual(self.order.global_discount_amount, 75.0)

    def test_max_amount_limit(self):
        self.env['ir.config_parameter'].set_float(
            'purchase_global_discount.max_discount_amount', 40.0,
        )
        with self.assertRaises(ValidationError):
            self.order.write({'discount_type': 'amount', 'discount_rate': 41})

    def test_amount_cannot_exceed_total(self):
        with self.assertRaises(ValidationError):
            self.order.write({'discount_type': 'amount', 'discount_rate': 501})

    def test_onchange_resets_rate_over_limit(self):
        self.env['ir.config_parameter'].set_float(
            'purchase_global_discount.max_discount_limit', 10.0,
        )
        order = self.env['purchase.order'].new({
            'partner_id': self.vendor.id,
            'discount_type': 'percent',
            'discount_rate': 50,
        })
        result = order._onchange_discount()
        self.assertEqual(order.discount_rate, 0)
        self.assertIn('warning', result)

    def test_confirm_keeps_discount(self):
        self.order.write({'discount_type': 'percent', 'discount_rate': 10})
        self.order.button_confirm()
        self.assertIn(self.order.state, ('purchase', 'to approve'))
        for line in self.order.order_line:
            self.assertAlmostEqual(line.discount, 10.0)
