# -*- coding: utf-8 -*-
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.exceptions import ValidationError
from odoo.fields import Command
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestQuickSale(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.group_ids |= (
            cls.env.ref('inom_quick_sale.group_quick_sale_manager')
            | cls.env.ref('sales_team.group_sale_manager')
            | cls.env.ref('stock.group_stock_manager')
        )
        cls.warehouse = cls.env['stock.warehouse'].search(
            [('company_id', '=', cls.env.company.id)], limit=1)
        cls.stock_location = cls.warehouse.lot_stock_id
        cls.product = cls.env['product.product'].create({
            'name': 'QS Storable',
            'is_storable': True,
            'list_price': 100.0,
            'invoice_policy': 'order',
            'taxes_id': [Command.clear()],
        })
        cls.partner = cls.partner_a

    def _set_param(self, key, value):
        self.env['ir.config_parameter'].sudo().set_bool(
            'inom_quick_sale.%s' % key, value == 'True')

    def _add_stock(self, qty, product=None, location=None):
        self.env['stock.quant']._update_available_quantity(
            product or self.product, location or self.stock_location, qty)

    def _create_quick_sale(self, qty=5.0, **vals):
        values = {
            'partner_id': self.partner.id,
            'quick_sale_type': 'quick_sale',
            'warehouse_id': self.warehouse.id,
            'order_line': [Command.create({
                'product_id': self.product.id,
                'product_uom_qty': qty,
            })],
        }
        values.update(vals)
        return self.env['sale.order'].create(values)

    def test_01_sequence(self):
        order = self._create_quick_sale()
        self.assertTrue(order.name.startswith('IN/SO'), order.name)
        regular = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'order_line': [Command.create({'product_id': self.product.id})],
        })
        self.assertFalse(regular.name.startswith('IN/SO'))

    def test_02_no_stock_blocks_confirm(self):
        order = self._create_quick_sale(qty=5)
        with self.assertRaises(ValidationError):
            order.action_confirm()

    def test_03_not_enough_stock_blocks_confirm(self):
        self._add_stock(2)
        order = self._create_quick_sale(qty=5)
        with self.assertRaises(ValidationError):
            order.action_confirm()

    def test_04_full_flow(self):
        self._add_stock(10)
        order = self._create_quick_sale(qty=5)
        order.action_confirm()
        self.assertEqual(order.state, 'sale')
        picking = order.picking_ids
        self.assertEqual(len(picking), 1)
        self.assertEqual(picking.state, 'done')
        self.assertEqual(picking.move_ids.quantity, 5)
        self.assertEqual(order.order_line.qty_delivered, 5)
        self.assertEqual(self.product.qty_available, 5)
        self.assertEqual(picking.quick_sale_order_id, order)
        invoice = order.invoice_ids
        self.assertEqual(len(invoice), 1)
        self.assertEqual(invoice.state, 'posted')
        self.assertEqual(invoice.amount_total, 500)

    def test_05_custom_source_location(self):
        sub_loc = self.env['stock.location'].create({
            'name': 'QS Shelf',
            'usage': 'internal',
            'location_id': self.stock_location.id,
        })
        self._add_stock(10, location=sub_loc)
        order = self._create_quick_sale(qty=3, source_location_id=sub_loc.id)
        order.action_confirm()
        picking = order.picking_ids
        self.assertEqual(picking.state, 'done')
        self.assertEqual(picking.location_id, sub_loc)
        self.assertEqual(picking.move_ids.move_line_ids.location_id, sub_loc)
        self.assertEqual(
            self.env['stock.quant']._get_available_quantity(self.product, sub_loc), 7)

    def test_06_no_auto_post(self):
        self._add_stock(10)
        self._set_param('auto_post_invoice', 'False')
        order = self._create_quick_sale(qty=1)
        order.action_confirm()
        self.assertEqual(order.invoice_ids.state, 'draft')

    def test_07_no_auto_delivery_no_invoice(self):
        self._add_stock(10)
        self._set_param('auto_validate_delivery', 'False')
        self._set_param('auto_create_invoice', 'False')
        order = self._create_quick_sale(qty=1)
        order.action_confirm()
        self.assertNotEqual(order.picking_ids.state, 'done')
        self.assertFalse(order.invoice_ids)

    def test_08_auto_payment(self):
        self._add_stock(10)
        self._set_param('auto_register_payment', 'True')
        order = self._create_quick_sale(qty=2)
        order.action_confirm()
        invoice = order.invoice_ids
        self.assertEqual(invoice.state, 'posted')
        self.assertIn(invoice.payment_state, ('paid', 'in_payment'))

    def test_09_cancel_returns_and_cancels_invoice(self):
        self._add_stock(10)
        order = self._create_quick_sale(qty=4)
        order.action_confirm()
        self.assertEqual(self.product.qty_available, 6)
        invoice = order.invoice_ids
        order.action_cancel()
        self.assertEqual(order.state, 'cancel')
        self.assertEqual(invoice.state, 'cancel')
        returns = order.picking_ids.filtered(lambda p: p.picking_type_code == 'incoming')
        self.assertEqual(len(returns), 1, 'A return picking should be created')
        self.assertEqual(returns.state, 'done')
        self.product.invalidate_recordset()
        self.assertEqual(self.product.qty_available, 10)

    def test_10_cancel_paid_invoice(self):
        self._add_stock(10)
        self._set_param('auto_register_payment', 'True')
        order = self._create_quick_sale(qty=1)
        order.action_confirm()
        invoice = order.invoice_ids
        order.action_cancel()
        self.assertEqual(invoice.state, 'cancel')

    def test_11_negative_stock_allowed(self):
        self._set_param('allow_negative_stock', 'True')
        order = self._create_quick_sale(qty=3)
        order.action_confirm()
        self.assertEqual(order.picking_ids.state, 'done')
        self.assertEqual(order.order_line.qty_delivered, 3)

    def test_12_multi_order_confirm(self):
        self._add_stock(10)
        orders = self._create_quick_sale(qty=2) | self._create_quick_sale(qty=3)
        orders.action_confirm()
        self.assertTrue(all(p.state == 'done' for p in orders.picking_ids))
        self.assertEqual(len(orders.invoice_ids), 2)

    def test_14_sequence_from_menu_context(self):
        order = self.env['sale.order'].with_context(
            default_quick_sale_type='quick_sale').create({
                'partner_id': self.partner.id,
                'order_line': [Command.create({'product_id': self.product.id})],
            })
        self.assertEqual(order.quick_sale_type, 'quick_sale')
        self.assertTrue(order.name.startswith('IN/SO'), order.name)

    def test_15_prefix_setting(self):
        self.env['res.config.settings'].create(
            {'quick_sale_sequence_prefix': 'QS/'}).execute()
        order = self._create_quick_sale()
        self.assertTrue(order.name.startswith('QS/'), order.name)

    def test_16_exact_stock_and_partial(self):
        self._add_stock(5)
        order = self._create_quick_sale(qty=5)
        order.action_confirm()
        self.assertEqual(order.picking_ids.state, 'done')
        self.assertEqual(order.order_line.qty_delivered, 5)

    def test_17_non_storable_consumable(self):
        consu = self.env['product.product'].create({
            'name': 'QS Consumable', 'is_storable': False, 'taxes_id': [Command.clear()]})
        order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'quick_sale_type': 'quick_sale',
            'order_line': [Command.create({'product_id': consu.id, 'product_uom_qty': 2})],
        })
        order.action_confirm()
        self.assertEqual(order.state, 'sale')
        self.assertEqual(order.order_line.qty_delivered, 2)

    def test_13_regular_order_untouched(self):
        self._add_stock(10)
        order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'order_line': [Command.create({'product_id': self.product.id, 'product_uom_qty': 1})],
        })
        order.action_confirm()
        self.assertNotEqual(order.picking_ids.state, 'done')
        self.assertFalse(order.invoice_ids)
