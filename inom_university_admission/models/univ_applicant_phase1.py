# -*- coding: utf-8 -*-
# Phase 1 - Application form completeness.
# Additive inherit: adds parent/guardian + nationality fields and small
# reusable helpers. Does NOT touch existing fields, create() or workflows.
from odoo import fields, models

# Single source of truth for the new website-capturable fields.
GUARDIAN_FIELDS = (
    "father_name", "father_phone", "father_email", "father_occupation",
    "mother_name", "mother_phone", "mother_email", "mother_occupation",
    "guardian_name", "guardian_relationship", "guardian_phone",
    "guardian_email", "guardian_occupation",
    "nationality",
)


class UnivApplicant(models.Model):
    _inherit = "univ.applicant"

    # ---- Nationality (independent from country_id) --------------------
    nationality = fields.Char(string="Nationality", tracking=True)

    # ---- Father ------------------------------------------------------
    father_name = fields.Char(string="Father's Name")
    father_phone = fields.Char(string="Father's Phone")
    father_email = fields.Char(string="Father's Email")
    father_occupation = fields.Char(string="Father's Occupation")

    # ---- Mother ------------------------------------------------------
    mother_name = fields.Char(string="Mother's Name")
    mother_phone = fields.Char(string="Mother's Phone")
    mother_email = fields.Char(string="Mother's Email")
    mother_occupation = fields.Char(string="Mother's Occupation")

    # ---- Guardian ----------------------------------------------------
    guardian_name = fields.Char(string="Guardian's Name")
    guardian_relationship = fields.Char(string="Guardian Relationship")
    guardian_phone = fields.Char(string="Guardian's Phone")
    guardian_email = fields.Char(string="Guardian's Email")
    guardian_occupation = fields.Char(string="Guardian's Occupation")

    # ------------------------------------------------------------------
    # Helper: pull the new website fields out of a POST dict.
    # Used by the website submit / draft / finalize controllers so the
    # mapping lives in one place.
    # ------------------------------------------------------------------
    def _website_extra_vals(self, post):
        return {f: post.get(f) for f in GUARDIAN_FIELDS if f in post}
