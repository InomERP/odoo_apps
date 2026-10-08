from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ResPartner(models.Model):
    _inherit = "res.partner"

    phone = fields.Char(string="Phone")

    customer_code = fields.Char(
        string="Customer Code",
    )

    _name_uniq = models.Constraint(
        "unique(customer_code)",
        "customer code must be unique!.",
    )

    @api.constrains("phone")
    def _check_phone_required(self):
        for rec in self:
            if not rec.phone:
                raise ValidationError("Phone number is mandatory.")

    def _assign_customer_code(self):
        """Assign the V19-style sequence to customers created without a code.

        Odoo 20 customer creation can be initiated from the Customers action
        through ``res_partner_search_mode=customer`` without setting
        ``customer_rank`` in the create values. Support both paths so the
        V19 behaviour is retained in V20.
        """
        sequence = self.env["ir.sequence"]
        customer_context = self.env.context.get("res_partner_search_mode") == "customer"
        for partner in self:
            if partner.customer_code:
                continue
            if partner.customer_rank > 0 or customer_context:
                partner.customer_code = sequence.next_by_code("res.partner")

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._assign_customer_code()
        return records

    def write(self, vals):
        result = super().write(vals)
        if "customer_rank" in vals or self.env.context.get("res_partner_search_mode") == "customer":
            self._assign_customer_code()
        return result
