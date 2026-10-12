# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    is_law_client = fields.Boolean(
        string="Law Firm Client", default=False, index=True, copy=False,
        help="Marks this contact as a client of the law firm.",
    )
    client_ref = fields.Char(string="Client Reference", copy=False, index=True, readonly=True)
    client_type = fields.Selection(
        [("individual", "Individual"), ("corporate", "Corporate")],
        string="Client Type", default="individual",
    )
    client_category_id = fields.Many2one("law.client.category", string="Client Category")
    law_client_since = fields.Date(string="Client Since")
    law_contact_count = fields.Integer(string="Contacts", compute="_compute_law_contact_count")

    def _compute_law_contact_count(self):
        for partner in self:
            partner.law_contact_count = len(partner.child_ids)

    def _assign_client_ref(self):
        for partner in self:
            if partner.is_law_client and not partner.client_ref:
                partner.client_ref = self.env["ir.sequence"].next_by_code("law.client") or "/"
            if partner.is_law_client and not partner.law_client_since:
                partner.law_client_since = fields.Date.context_today(partner)

    @api.model_create_multi
    def create(self, vals_list):
        partners = super().create(vals_list)
        partners._assign_client_ref()
        return partners

    def write(self, vals):
        res = super().write(vals)
        if vals.get("is_law_client"):
            self._assign_client_ref()
        return res

    def action_view_law_contacts(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Contacts",
            "res_model": "res.partner",
            "domain": [("parent_id", "=", self.id)],
            "view_mode": "kanban,list,form",
            "context": {"default_parent_id": self.id},
        }
