# -*- coding: utf-8 -*-
from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    inom_substitution_history_ids = fields.One2many(
        comodel_name="inom.product.substitution.history",
        inverse_name="order_id",
        string="Substitution History",
        help="Audit trail of product replacements performed on this order.",
    )
    inom_substitution_history_count = fields.Integer(
        string="Substitution History Count",
        compute="_compute_inom_substitution_history_count",
        help="Number of product replacements recorded on this order. Used by "
             "the Substitution History smart button.",
    )

    @api.depends("inom_substitution_history_ids")
    def _compute_inom_substitution_history_count(self):
        for order in self:
            order.inom_substitution_history_count = len(
                order.inom_substitution_history_ids
            )

    def action_inom_view_substitution_history(self):
        """Open the substitution history records of this order."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Substitution History",
            "res_model": "inom.product.substitution.history",
            "view_mode": "tree,form",
            "domain": [("order_id", "=", self.id)],
            "context": {"create": False, "default_order_id": self.id},
            "target": "current",
        }
