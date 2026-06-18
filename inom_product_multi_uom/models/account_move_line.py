# -*- coding: utf-8 -*-
from odoo import fields, models


class AccountMoveLine(models.Model):
    """Carry the secondary UoM reference from the sale line to the invoice
    line (F-11). The invoice quantity stays the correct base quantity; these
    fields only document the secondary UoM the sale was made in.
    """

    _inherit = "account.move.line"

    secondary_uom_id = fields.Many2one(
        comodel_name="uom.uom",
        string="Secondary UoM",
        copy=False,
        help="Secondary Unit of Measure the originating sale line was made "
             "in (reference only).",
    )
    secondary_qty = fields.Float(
        string="Secondary Qty",
        digits="Product Unit of Measure",
        copy=False,
        help="Quantity in the secondary UoM on the originating sale line "
             "(reference only).",
    )
