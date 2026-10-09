from psycopg2 import IntegrityError

from odoo import Command
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.exceptions import AccessError
from odoo.tests import Form, new_test_user, tagged
from odoo.tests.common import TransactionCase
from odoo.tools import mute_logger


@tagged('post_install', '-at_install')
class TestMultiBarcode(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Barcode = cls.env['product.multiple.barcodes']
        cls.template = cls.env['product.template'].create({
            'name': 'Multi Barcode Template',
            'template_multi_barcode_ids': [
                Command.create({'product_multi_barcode': 'MB-T-1'}),
                Command.create({'product_multi_barcode': 'MB-T-2'}),
            ],
        })
        cls.variant = cls.env['product.product'].create({
            'name': 'Multi Barcode Variant',
            'multi_barcode_ids': [Command.create({'product_multi_barcode': 'MB-V-1'})],
        })

    def test_template_barcodes_link_variant(self):
        barcodes = self.template.template_multi_barcode_ids
        self.assertEqual(len(barcodes), 2)
        self.assertEqual(barcodes.product_id, self.template.product_variant_id)

    def test_variant_barcodes_link_template(self):
        self.assertEqual(self.variant.multi_barcode_ids.product_template_id, self.variant.product_tmpl_id)
        self.assertEqual(self.variant.product_tmpl_id.template_multi_barcode_ids, self.variant.multi_barcode_ids)

    def test_batch_create(self):
        templates = self.env['product.template'].create([
            {'name': 'Batch A', 'template_multi_barcode_ids': [Command.create({'product_multi_barcode': 'MB-BA'})]},
            {'name': 'Batch B', 'template_multi_barcode_ids': [Command.create({'product_multi_barcode': 'MB-BB'})]},
        ])
        for template in templates:
            self.assertEqual(template.template_multi_barcode_ids.product_id, template.product_variant_id)
        variants = self.env['product.product'].create([
            {'name': 'Batch C', 'multi_barcode_ids': [Command.create({'product_multi_barcode': 'MB-BC'})]},
            {'name': 'Batch D', 'multi_barcode_ids': [Command.create({'product_multi_barcode': 'MB-BD'})]},
        ])
        for variant in variants:
            self.assertEqual(variant.multi_barcode_ids.product_template_id, variant.product_tmpl_id)

    def test_add_barcode_on_existing_template(self):
        self.template.write({'template_multi_barcode_ids': [Command.create({'product_multi_barcode': 'MB-T-3'})]})
        new_barcode = self.template.template_multi_barcode_ids.filtered(lambda b: b.product_multi_barcode == 'MB-T-3')
        self.assertEqual(new_barcode.product_id, self.template.product_variant_id)

    def test_barcode_must_be_unique(self):
        with mute_logger('odoo.sql_db'), self.assertRaises(IntegrityError):
            self.Barcode.create({'product_multi_barcode': 'MB-T-1', 'product_id': self.variant.id})
            self.env.flush_all()

    def test_template_edit_keeps_variant_barcodes(self):
        attribute = self.env['product.attribute'].create({
            'name': 'Size',
            'value_ids': [Command.create({'name': 'S'}), Command.create({'name': 'M'})],
        })
        template = self.env['product.template'].create({
            'name': 'Sized Product',
            'attribute_line_ids': [Command.create({
                'attribute_id': attribute.id,
                'value_ids': [Command.set(attribute.value_ids.ids)],
            })],
        })
        variant_m = template.product_variant_ids[1]
        variant_m.write({'multi_barcode_ids': [Command.create({'product_multi_barcode': 'MB-SIZE-M'})]})
        template.write({'name': 'Sized Product (renamed)'})
        self.assertEqual(variant_m.multi_barcode_ids.product_multi_barcode, 'MB-SIZE-M')
        self.assertEqual(variant_m.multi_barcode_ids.product_template_id, template)

    def test_template_delete_removes_barcodes(self):
        barcodes = self.template.template_multi_barcode_ids
        self.template.unlink()
        self.assertFalse(barcodes.exists())

    def test_search_read_by_multi_barcode(self):
        result = self.env['product.product'].search_read([('barcode', '=', 'MB-T-2')], ['id'])
        self.assertEqual([r['id'] for r in result], [self.template.product_variant_id.id])
        result = self.env['product.product'].search_read([('barcode', '=', 'MB-V-1')], ['uom_id'], load=None)
        self.assertEqual(result[0]['id'], self.variant.id)
        self.assertIsInstance(result[0]['uom_id'], int)

    def test_search_read_unknown_barcode(self):
        result = self.env['product.product'].search_read([('barcode', '=', 'MB-UNKNOWN')], ['id'])
        self.assertEqual(result, [])

    def test_template_search_by_multi_barcode(self):
        found = self.env['product.template'].search([('template_multi_barcode_ids.product_multi_barcode', 'ilike', 'MB-T-2')])
        self.assertEqual(found, self.template)

    def test_access_rights(self):
        user = new_test_user(self.env, login='mb_user', groups='base.group_user')
        manager = new_test_user(self.env, login='mb_manager', groups='base.group_user,product.group_product_manager')
        self.assertTrue(self.Barcode.with_user(user).search([('product_multi_barcode', '=', 'MB-T-1')]))
        with self.assertRaises(AccessError):
            self.Barcode.with_user(user).create({'product_multi_barcode': 'MB-USER', 'product_id': self.variant.id})
        barcode = self.Barcode.with_user(manager).create({'product_multi_barcode': 'MB-MANAGER', 'product_id': self.variant.id})
        self.assertEqual(barcode.product_template_id, self.variant.product_tmpl_id)


@tagged('post_install', '-at_install')
class TestMultiBarcodeOrders(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.group_ids |= cls.env.ref('sales_team.group_sale_salesman')
        cls.product = cls.env['product.product'].create({
            'name': 'Scanned Product',
            'multi_barcode_ids': [Command.create({'product_multi_barcode': 'MB-ORDER-1'})],
        })

    def test_sale_order_line_scan(self):
        with Form(self.env['sale.order']) as order_form:
            order_form.partner_id = self.partner_a
            with order_form.order_line.new() as line:
                line.scan_barcode = 'MB-ORDER-1'
                self.assertEqual(line.product_id, self.product)
        order = order_form.record
        self.assertEqual(order.order_line.scan_barcode, 'MB-ORDER-1')
        self.assertEqual(order.order_line._prepare_invoice_line()['scan_barcode'], 'MB-ORDER-1')

    def test_purchase_order_line_scan_and_bill(self):
        with Form(self.env['purchase.order']) as order_form:
            order_form.partner_id = self.partner_a
            with order_form.order_line.new() as line:
                line.scan_barcode = 'MB-ORDER-1'
                self.assertEqual(line.product_id, self.product)
        order = order_form.record
        order.button_confirm()
        order.order_line.qty_received = order.order_line.product_qty
        bill = self.env['account.move'].browse(order.action_create_invoice()['res_id'])
        self.assertEqual(bill.invoice_line_ids.filtered('product_id').scan_barcode, 'MB-ORDER-1')

    def test_account_move_line_scan(self):
        line = self.env['account.move.line'].new({'scan_barcode': 'MB-ORDER-1'})
        line._onchange_scan_barcode()
        self.assertEqual(line.product_id, self.product)
