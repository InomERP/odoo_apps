# -*- coding: utf-8 -*-
# Part of INOM Sale Order Label Print. See LICENSE file for full copyright
# and licensing details.
from odoo import _, models
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_print_inom_labels(self):
        """Open the INOM Label Builder print wizard, pre-filled with one
        line per order line product/quantity, so labels for the whole
        order can be printed without leaving the Sale Order.

        The heavy lifting (building the label lines, choosing the label
        type, defaulting the template, etc.) is delegated to
        ``inom.label.print.wizard._action_open_for`` /
        ``default_get`` in the ``inom_label_builder`` module, which
        already knows how to read ``sale.order`` lines.
        """
        self.ensure_one()
        if not self.order_line.filtered('product_id'):
            raise UserError(_(
                'There are no products on this order to print labels '
                'for.'))
        return self.env['inom.label.print.wizard']._action_open_for(
            'sale.order', self.ids)
