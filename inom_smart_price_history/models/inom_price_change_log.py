# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class InomPriceChangeLog(models.Model):
    _name = "inom.price.change.log"
    _description = "Product Price Change Log"
    _order = "change_date desc, id desc"
    _rec_name = "product_id"

    product_id = fields.Many2one(
        comodel_name="product.product",
        string="Product",
        required=True,
        ondelete="cascade",
        index=True,
    )
    product_tmpl_id = fields.Many2one(
        comodel_name="product.template",
        string="Product Template",
        related="product_id.product_tmpl_id",
        store=True,
        index=True,
    )
    source = fields.Selection(
        selection=[
            ("invoice", "Customer Invoice"),
            ("bill", "Vendor Bill"),
            ("purchase", "Purchase Order"),
            ("cost", "Cost Update"),
        ],
        string="Source",
        required=True,
        index=True,
    )
    old_price = fields.Monetary(
        string="Old Price",
        currency_field="currency_id",
    )
    new_price = fields.Monetary(
        string="New Price",
        currency_field="currency_id",
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        string="Currency",
    )
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Partner",
        help="Customer for invoice changes or vendor for purchase changes.",
    )
    reference = fields.Char(string="Reference")
    move_id = fields.Many2one(
        comodel_name="account.move",
        string="Invoice",
        ondelete="set null",
    )
    purchase_order_id = fields.Many2one(
        comodel_name="purchase.order",
        string="Purchase Order",
        ondelete="set null",
    )
    change_date = fields.Datetime(
        string="Change Date",
        default=fields.Datetime.now,
        index=True,
    )
    user_id = fields.Many2one(
        comodel_name="res.users",
        string="Changed By",
        default=lambda self: self.env.user,
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        default=lambda self: self.env.company,
        index=True,
    )

    @api.model
    def log_price_change(self, product, source, old_price, new_price,
                         currency=None, partner=None, move=None,
                         purchase_order=None, reference=False, company=None):
        """Centralised helper to record a single price change entry.

        The record is created with sudo() because the originating action (for
        example editing a customer invoice or a purchase order) may be performed
        by a user who does not hold create rights on this internal audit model.
        The data written is strictly limited to the document the user is already
        editing, so no unrelated information can be exposed.
        """
        if not product:
            return self.browse()
        company = company or self.env.company
        currency = currency or company.currency_id
        return self.sudo().create({
            "product_id": product.id,
            "source": source,
            "old_price": old_price,
            "new_price": new_price,
            "currency_id": currency.id if currency else False,
            "partner_id": partner.id if partner else False,
            "move_id": move.id if move else False,
            "purchase_order_id": purchase_order.id if purchase_order else False,
            "reference": reference,
            "company_id": company.id,
        })