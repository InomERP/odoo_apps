# -*- coding: utf-8 -*-
# Phase 5 - Subject prerequisites. Added via an academics inherit so the core
# univ.subject model is left untouched.
from odoo import fields, models


class UnivSubject(models.Model):
    _inherit = "univ.subject"

    prerequisite_ids = fields.Many2many(
        comodel_name="univ.subject",
        relation="univ_subject_prerequisite_rel",
        column1="subject_id",
        column2="prerequisite_id",
        string="Prerequisites",
        domain="[('id', '!=', id)]",
        help="Subjects that must be passed before this subject can be "
        "registered.",
    )
