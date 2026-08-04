# -*- coding: utf-8 -*-
from odoo import fields, models


class LawCase(models.Model):
    _inherit = "law.case"

    cited_case_law_ids = fields.Many2many("law.case.law", string="Cited Case Law")
    referenced_act_ids = fields.Many2many("law.act", string="Referenced Acts")
