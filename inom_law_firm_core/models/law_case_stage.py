# -*- coding: utf-8 -*-
from odoo import fields, models


class LawCaseStage(models.Model):
    _name = "law.case.stage"
    _description = "Legal Case Stage"
    _order = "sequence, id"

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=10)
    fold = fields.Boolean(
        string="Folded in Kanban",
        help="Fold this stage in the case kanban view when it has no records to display.",
    )
    is_closing = fields.Boolean(
        string="Closing Stage",
        help="Cases in a closing stage are considered closed.",
    )
    active = fields.Boolean(default=True)
    company_id = fields.Many2one("res.company", string="Company")
    description = fields.Text()
