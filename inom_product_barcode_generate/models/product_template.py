from odoo import models, api
from odoo.exceptions import ValidationError
import random

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('barcode'):
                vals['barcode'] = self._generate_unique_ean13()
        return super().create(vals_list)

    # Button: reGenerate barcode manually
    def action_regenerate_barcode(self):
        for rec in self:
            rec.barcode = self._generate_unique_ean13()

    def _generate_unique_ean13(self):
    	product = self.env['product.template']

    	while True:
    		digits = [random.randint(0,9)for _ in range(12)]

    		#checksum logic
    		even_sum = sum(digits[i] for i in range(1,12,2))
    		odd_sum = sum(digits[i] for i in range(0,12,2))
    		total = odd_sum + (even_sum*3)
    		check_digit = (10 - (total%10))%10

    		barcode = ''.join(map(str, digits)) + str(check_digit)

    		if not product.search([('barcode', '=', barcode)], limit=1):
    			return barcode
