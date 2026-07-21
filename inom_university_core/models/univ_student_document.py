# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class UnivStudentDocument(models.Model):
    _name = "univ.student.document"
    _description = "Student Document"
    _inherit = ["mail.thread"]
    _order = "student_id, doc_type, version desc"

    name = fields.Char(string="Document Name", required=True)
    student_id = fields.Many2one(
        comodel_name="univ.student",
        string="Student",
        required=True,
        ondelete="cascade",
        index=True,
    )
    doc_type = fields.Selection(
        selection=[
            ("tenth", "10th Marksheet"),
            ("twelfth", "12th Marksheet"),
            ("transfer", "Transfer Certificate"),
            ("migration", "Migration Certificate"),
            ("id_proof", "ID Proof"),
            ("photo", "Photograph"),
            ("other", "Other"),
        ],
        string="Document Type",
        required=True,
        tracking=True,
    )
    version = fields.Integer(string="Version", default=1, readonly=True)
    file = fields.Binary(string="File", attachment=True)
    file_name = fields.Char(string="File Name")
    state = fields.Selection(
        selection=[
            ("pending", "Pending"),
            ("verified", "Verified"),
            ("rejected", "Rejected"),
        ],
        string="Status",
        default="pending",
        required=True,
        tracking=True,
    )
    issue_date = fields.Date(string="Issue Date")
    expiry_date = fields.Date(string="Expiry Date")
    verified_by = fields.Many2one(
        comodel_name="res.users", string="Verified By", readonly=True
    )
    verified_date = fields.Datetime(string="Verified On", readonly=True)
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Campus",
        related="student_id.company_id",
        store=True,
        index=True,
        readonly=True,
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("student_id") and vals.get("doc_type"):
                existing = self.search(
                    [
                        ("student_id", "=", vals["student_id"]),
                        ("doc_type", "=", vals["doc_type"]),
                    ],
                    order="version desc",
                    limit=1,
                )
                if existing:
                    vals["version"] = existing.version + 1
        return super().create(vals_list)

    def action_verify(self):
        for record in self:
            if not record.file:
                raise UserError(
                    _("Cannot verify a document with no file attached.")
                )
            record.write(
                {
                    "state": "verified",
                    "verified_by": self.env.user.id,
                    "verified_date": fields.Datetime.now(),
                }
            )

    def action_reject(self):
        self.write(
            {
                "state": "rejected",
                "verified_by": self.env.user.id,
                "verified_date": fields.Datetime.now(),
            }
        )

    def action_reset(self):
        self.write(
            {"state": "pending", "verified_by": False, "verified_date": False}
        )
