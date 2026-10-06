# -*- coding: utf-8 -*-
from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestVendorProduct(TransactionCase):
    """Main write path of vendor.product."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.vendor = cls.env['res.partner'].create({
            'name': 'Acme Supplies',
            'supplier_rank': 1,
        })
        cls.customer = cls.env['res.partner'].create({
            'name': 'Plain Customer',
            'supplier_rank': 0,
        })
        cls.product = cls.env['product.product'].create({
            'name': 'Internal Widget',
            'default_code': 'WID-01',
        })

    def test_create_and_display_name(self):
        vp = self.env['vendor.product'].create({
            'vendor_id': self.vendor.id,
            'vendor_product_name': 'Acme Widget',
            'vendor_code': 'ACME-77',
            'product_id': self.product.id,
        })
        self.assertTrue(vp.active)
        self.assertEqual(vp.product_tmpl_id, self.product.product_tmpl_id)
        self.assertEqual(vp.display_name, 'Acme Supplies - [ACME-77] Acme Widget')

    def test_vendor_must_be_supplier(self):
        with self.assertRaises(ValidationError):
            self.env['vendor.product'].create({
                'vendor_id': self.customer.id,
                'vendor_product_name': 'Should Fail',
            })

    def test_write_price_fields(self):
        vp = self.env['vendor.product'].create({
            'vendor_id': self.vendor.id,
            'vendor_product_name': 'Priced Item',
        })
        vp.write({'vendor_price': 42.5, 'price_outdated': True})
        self.assertEqual(vp.vendor_price, 42.5)
        self.assertTrue(vp.price_outdated)


class TestVendorLocation(TransactionCase):
    """Main write path of vendor.location."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.vendor = cls.env['res.partner'].create({
            'name': 'Acme Supplies',
            'supplier_rank': 1,
        })

    def test_create_and_display_name(self):
        loc = self.env['vendor.location'].create({
            'vendor_id': self.vendor.id,
            'name': 'Main Warehouse',
            'address': 'Industrial Zone 5',
            'delivery_lead_time': 3.0,
        })
        self.assertTrue(loc.active)
        self.assertEqual(loc.display_name, 'Acme Supplies - Main Warehouse')


class TestVendorStock(TransactionCase):
    """Main write path of vendor.stock, including UoM conversion."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.vendor = cls.env['res.partner'].create({
            'name': 'Acme Supplies',
            'supplier_rank': 1,
        })
        cls.uom_unit = cls.env.ref('uom.product_uom_unit')
        cls.uom_dozen = cls.env['uom.uom'].create({
            'name': 'Test Dozen Pack',
            'relative_uom_id': cls.uom_unit.id,
            'relative_factor': 12.0,
        })
        cls.uom_alien = cls.env['uom.uom'].create({
            'name': 'Test Root Unit',
        })
        cls.product = cls.env['product.product'].create({
            'name': 'Internal Widget',
            'uom_id': cls.uom_unit.id,
        })
        cls.vendor_product = cls.env['vendor.product'].create({
            'vendor_id': cls.vendor.id,
            'vendor_product_name': 'Acme Widget',
            'vendor_code': 'ACME-77',
            'product_id': cls.product.id,
        })
        cls.location = cls.env['vendor.location'].create({
            'vendor_id': cls.vendor.id,
            'name': 'Main Warehouse',
        })

    def test_uom_conversion_same_category(self):
        stock = self.env['vendor.stock'].create({
            'vendor_product_id': self.vendor_product.id,
            'location_id': self.location.id,
            'quantity': 2.0,
            'uom_id': self.uom_dozen.id,
        })
        self.assertFalse(stock.uom_mismatch)
        self.assertEqual(stock.quantity_product_uom, 24.0)
        self.assertEqual(self.vendor_product.total_vendor_stock_qty, 24.0)
        self.assertEqual(self.vendor_product.vendor_stock_count, 1)

    def test_uom_mismatch_flag(self):
        stock = self.env['vendor.stock'].create({
            'vendor_product_id': self.vendor_product.id,
            'location_id': self.location.id,
            'quantity': 5.0,
            'uom_id': self.uom_alien.id,
        })
        self.assertTrue(stock.uom_mismatch)
        self.assertEqual(stock.quantity_product_uom, 5.0)

    def test_archive_stock_line(self):
        stock = self.env['vendor.stock'].create({
            'vendor_product_id': self.vendor_product.id,
            'location_id': self.location.id,
            'quantity': 10.0,
            'uom_id': self.uom_unit.id,
        })
        stock.write({'active': False})
        self.assertFalse(stock.active)
