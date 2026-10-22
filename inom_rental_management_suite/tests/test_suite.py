from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestRentalManagementSuite(TransactionCase):

    def test_suite_installs_all_modules(self):
        names = [
            'inom_rental_management',
            'inom_rental_management_website',
            'inom_rental_management_maintenance',
            'inom_rental_management_suite',
        ]
        modules = self.env['ir.module.module'].search([('name', 'in', names)])
        self.assertEqual(set(modules.mapped('name')), set(names))
        self.assertEqual(set(modules.mapped('state')), {'installed'})
