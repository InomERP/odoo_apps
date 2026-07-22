# -*- coding: utf-8 -*-
from odoo import api, fields, models


class UnivFeeHead(models.Model):
    _name = "univ.fee.head"
    _description = "Fee Head"
    _order = "sequence, name"

    name = fields.Char(string="Fee Head", required=True, translate=True)
    code = fields.Char(string="Code")
    sequence = fields.Integer(string="Sequence", default=10)
    category_id = fields.Many2one(
        comodel_name="univ.fee.category", string="Category"
    )
    group_id = fields.Many2one(
        comodel_name="univ.fee.group", string="Fee Group"
    )
    product_id = fields.Many2one(
        comodel_name="product.product",
        string="Product",
        required=True,
        help="Service product used on the invoice line for this fee head.",
    )
    account_id = fields.Many2one(
        comodel_name="account.account",
        string="Income Account",
        help="Income account for this head. Defaults to the product income "
             "account when empty.",
    )
    tax_ids = fields.Many2many(
        comodel_name="account.tax",
        string="Default Taxes",
        domain="[('type_tax_use', '=', 'sale')]",
    )
    refundable = fields.Boolean(string="Refundable", default=True)
    active = fields.Boolean(string="Active", default=True)
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        default=lambda self: self.env.company,
        index=True,
    )

    _sql_constraints = [
        ("code_uniq", "unique(code, company_id)",
         "The fee head code must be unique per company."),
    ]

    @api.onchange("product_id")
    def _onchange_product_id(self):
        for head in self:
            if head.product_id and not head.account_id:
                head.account_id = (
                    head.product_id.property_account_income_id
                    or head.product_id.categ_id.property_account_income_categ_id
                )
            if head.product_id and not head.tax_ids:
                head.tax_ids = head.product_id.taxes_id

    def _get_income_account(self):
        self.ensure_one()
        return (
            self.account_id
            or self.product_id.property_account_income_id
            or self.product_id.categ_id.property_account_income_categ_id
        )
