# -*- coding: utf-8 -*-
# Phase 4 - Deposit linkage on the native invoice (account.move). The deposit
# IS a normal posted customer invoice; these fields just tag it and link it back
# to the admission record so it is traceable to Applicant / Program / Student.
from odoo import fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    is_univ_deposit = fields.Boolean(
        string="Admission Deposit", copy=False, default=False, index=True
    )
    univ_deposit_applicant_id = fields.Many2one(
        comodel_name="univ.applicant",
        string="Admission Applicant",
        copy=False,
        index=True,
        ondelete="set null",
    )
    univ_deposit_program_id = fields.Many2one(
        comodel_name="univ.program",
        string="Admission Program",
        related="univ_deposit_applicant_id.program_id",
        store=True,
    )
    univ_deposit_student_id = fields.Many2one(
        comodel_name="univ.student",
        string="Admission Student",
        related="univ_deposit_applicant_id.student_id",
        store=True,
    )
