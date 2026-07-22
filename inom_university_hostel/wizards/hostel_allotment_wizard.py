# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class UnivHostelAllotmentWizard(models.TransientModel):
    _name = "univ.hostel.allotment.wizard"
    _description = "Allot Hostel Bed"

    student_id = fields.Many2one(comodel_name="univ.student", string="Student",
                                 required=True)
    hostel_id = fields.Many2one(comodel_name="univ.hostel", string="Hostel",
                                required=True)
    bed_id = fields.Many2one(comodel_name="univ.hostel.bed", string="Bed",
                             required=True,
                             domain="[('hostel_id', '=', hostel_id), ('state', '=', 'available')]")
    deposit_amount = fields.Monetary(string="Security Deposit")
    hostel_fee = fields.Monetary(string="Hostel Fee")
    fee_head_id = fields.Many2one(comodel_name="univ.fee.head",
                                  string="Hostel Fee Head", required=True)
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        default=lambda self: self.env.company.currency_id)

    def action_allot(self):
        self.ensure_one()
        if self.bed_id.state != "available":
            raise UserError(_("Bed is no longer available."))
        allotment = self.env["univ.hostel.allotment"].create({
            "student_id": self.student_id.id,
            "hostel_id": self.hostel_id.id,
            "bed_id": self.bed_id.id,
            "deposit_amount": self.deposit_amount,
            "hostel_fee": self.hostel_fee,
            "fee_head_id": self.fee_head_id.id,
        })
        allotment.action_allot()
        return {
            "type": "ir.actions.act_window",
            "res_model": "univ.hostel.allotment",
            "res_id": allotment.id,
            "view_mode": "form",
            "target": "current",
        }
