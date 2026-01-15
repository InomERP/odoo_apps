from odoo import models, fields, api
from odoo.exceptions import ValidationError


class ResPartner(models.Model):
    _inherit = 'res.partner'

    customer_code = fields.Char(
        string="Customer Code"
    )


    # Make customer_code unique
    _sql_constraints = [
        ('customer_code_unique', 'unique(customer_code)', 'customer code must be unique!')
    ]

    @api.constrains('phone')
    def _check_phone_required(self):
        for rec in self:
            if not rec.phone:
                raise ValidationError("Phone number is mandatory.")

    @api.model_create_multi
    def create(self,vals_list):
        print("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",vals_list)
        for vals in vals_list:
            print("jjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjj",vals.get("customer_rank"),vals.get("customer_code"))
            if vals.get("customer_rank") ==1 and not vals.get("customer_code"):
                print("ffffffffffffffffffffffff")
                vals["customer_code"] = self.env["ir.sequence"].next_by_code("res.partner")
                print("vvvvvvvvvvvvvvvvvvvvvvvv",vals["customer_code"])
        return super().create(vals_list)
