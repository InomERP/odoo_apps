# -*- coding: utf-8 -*-
import base64
import io

from odoo.tests.common import TransactionCase

try:
    from openpyxl import Workbook
except ImportError:  # pragma: no cover
    Workbook = None


def _xlsx(rows):
    """Build an in-memory xlsx (header row + data rows) as base64."""
    wb = Workbook()
    ws = wb.active
    for row in rows:
        ws.append(row)
    buf = io.BytesIO()
    wb.save(buf)
    return base64.b64encode(buf.getvalue()).decode()


class TestVendorProductImportWizard(TransactionCase):
    """Main write path of the products & prices import."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.vendor = cls.env['res.partner'].create({
            'name': 'Acme Supplies',
            'supplier_rank': 1,
        })
        cls.product = cls.env['product.product'].create({
            'name': 'Internal Widget',
            'default_code': 'WID-01',
        })
        cls.headers = [
            'Import (Yes/No)', 'Vendor Product Code', 'Vendor Product Name',
            'Internal Product Reference', 'Vendor Price', 'Notes',
        ]

    def _run(self, rows, **options):
        wizard = self.env['vendor.product.import.wizard'].create({
            'vendor_id': self.vendor.id,
            'import_file': _xlsx([self.headers] + rows),
            'import_filename': 'test.xlsx',
            **options,
        })
        action = wizard.action_import()
        return self.env['vendor.import.result'].browse(action['res_id'])

    def test_import_creates_and_links(self):
        result = self._run([
            ['Yes', 'ACME-1', 'Acme Widget', 'WID-01', 19.9, 'first'],
            ['Yes', 'ACME-2', 'Acme Gadget', '', 5.0, ''],
        ])
        self.assertEqual(result.created_count, 2)
        self.assertEqual(result.error_count, 0)
        vp = self.env['vendor.product'].search([
            ('vendor_id', '=', self.vendor.id), ('vendor_code', '=', 'ACME-1'),
        ])
        self.assertEqual(len(vp), 1)
        self.assertEqual(vp.product_id, self.product)
        self.assertEqual(vp.vendor_price, 19.9)
        self.assertFalse(vp.price_outdated)

    def test_import_updates_existing(self):
        existing = self.env['vendor.product'].create({
            'vendor_id': self.vendor.id,
            'vendor_product_name': 'Old Name',
            'vendor_code': 'ACME-1',
            'vendor_price': 10.0,
        })
        result = self._run(
            [['Yes', 'ACME-1', 'New Name', '', 12.0, '']],
            mark_previous_prices_outdated=True,
        )
        self.assertEqual(result.updated_count, 1)
        self.assertEqual(existing.vendor_product_name, 'New Name')
        self.assertEqual(existing.vendor_price, 12.0)
        self.assertFalse(existing.price_outdated)

    def test_archive_other_products(self):
        keep = self.env['vendor.product'].create({
            'vendor_id': self.vendor.id,
            'vendor_product_name': 'In File',
            'vendor_code': 'ACME-1',
        })
        drop = self.env['vendor.product'].create({
            'vendor_id': self.vendor.id,
            'vendor_product_name': 'Not In File',
            'vendor_code': 'ACME-9',
        })
        result = self._run(
            [
                ['Yes', 'ACME-1', 'In File', '', '', ''],
                ['Yes', '', 'Name Only Row', '', '', ''],
            ],
            archive_other_products=True,
        )
        self.assertEqual(result.archived_count, 1)
        self.assertTrue(keep.active)
        self.assertFalse(drop.active)
        name_only = self.env['vendor.product'].search([
            ('vendor_id', '=', self.vendor.id),
            ('vendor_product_name', '=', 'Name Only Row'),
        ])
        self.assertTrue(name_only.active, "rows imported in this run must never be archived")

    def test_only_chosen_lines_and_errors(self):
        result = self._run(
            [
                ['No', 'ACME-1', 'Skipped Row', '', '', ''],
                ['Yes', 'ACME-2', '', '', '', ''],
                ['Yes', 'ACME-3', 'Bad Price', '', 'abc', ''],
                ['Yes', 'ACME-4', 'Bad Ref', 'NOPE-99', 1.0, ''],
            ],
            import_only_chosen_lines=True,
        )
        self.assertEqual(result.skipped_count, 1)
        self.assertEqual(result.error_count, 3)
        self.assertEqual(result.created_count, 2)


class TestVendorStockImportWizard(TransactionCase):
    """Main write path of the products & stocks import."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.vendor = cls.env['res.partner'].create({
            'name': 'Acme Supplies',
            'supplier_rank': 1,
        })
        cls.uom_unit = cls.env.ref('uom.product_uom_unit')
        cls.product = cls.env['product.product'].create({
            'name': 'Internal Widget',
            'uom_id': cls.uom_unit.id,
        })
        cls.vendor_product = cls.env['vendor.product'].create({
            'vendor_id': cls.vendor.id,
            'vendor_product_name': 'Acme Widget',
            'vendor_code': 'ACME-1',
            'product_id': cls.product.id,
        })
        cls.headers = [
            'Import (Yes/No)', 'Vendor Product Code', 'Vendor Location',
            'Quantity', 'Vendor UoM', 'Notes',
        ]

    def _run(self, rows, **options):
        wizard = self.env['vendor.stock.import.wizard'].create({
            'vendor_id': self.vendor.id,
            'import_file': _xlsx([self.headers] + rows),
            'import_filename': 'test.xlsx',
            **options,
        })
        action = wizard.action_import()
        return self.env['vendor.import.result'].browse(action['res_id'])

    def test_import_creates_stock_and_location(self):
        result = self._run([
            ['Yes', 'ACME-1', 'Main Warehouse', 100, self.uom_unit.name, 'note'],
        ])
        self.assertEqual(result.created_count, 1)
        self.assertEqual(result.error_count, 0)
        location = self.env['vendor.location'].search([
            ('vendor_id', '=', self.vendor.id), ('name', '=', 'Main Warehouse'),
        ])
        self.assertEqual(len(location), 1, "missing location must be auto-created")
        stock = self.env['vendor.stock'].search([
            ('vendor_product_id', '=', self.vendor_product.id),
            ('location_id', '=', location.id),
        ])
        self.assertEqual(stock.quantity, 100.0)
        self.assertEqual(stock.uom_id, self.uom_unit)

    def test_import_updates_and_archives(self):
        location = self.env['vendor.location'].create({
            'vendor_id': self.vendor.id, 'name': 'Main Warehouse',
        })
        old_line = self.env['vendor.stock'].create({
            'vendor_product_id': self.vendor_product.id,
            'location_id': location.id,
            'quantity': 5.0,
            'uom_id': self.uom_unit.id,
        })
        other_location = self.env['vendor.location'].create({
            'vendor_id': self.vendor.id, 'name': 'Old Depot',
        })
        stale_line = self.env['vendor.stock'].create({
            'vendor_product_id': self.vendor_product.id,
            'location_id': other_location.id,
            'quantity': 1.0,
            'uom_id': self.uom_unit.id,
        })
        result = self._run(
            [['Yes', 'ACME-1', 'Main Warehouse', 50, self.uom_unit.name, '']],
            archive_previous_stocks=True,
        )
        self.assertEqual(result.updated_count, 1)
        self.assertEqual(old_line.quantity, 50.0)
        self.assertTrue(old_line.active)
        self.assertFalse(stale_line.active)

    def test_unknown_code_is_reported(self):
        result = self._run([
            ['Yes', 'NOPE-99', 'Main Warehouse', 10, '', ''],
        ])
        self.assertEqual(result.created_count, 0)
        self.assertEqual(result.error_count, 1)
