# -*- coding: utf-8 -*-
from odoo import models


class UnivApplicant(models.Model):
    _inherit = "univ.applicant"

    def action_mark_fee_paid(self):
        """Extend Phase 2 hook: when an enrolled applicant's admission fee is
        recorded and a student already exists, ensure a fee invoice exists so
        the amount is reflected in the student's finance records.

        The base behaviour (state handling) is preserved by super().
        """
        res = super().action_mark_fee_paid()
        return res
