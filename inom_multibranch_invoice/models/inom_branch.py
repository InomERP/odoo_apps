# -*- coding: utf-8 -*-
from odoo import api, fields, models


class InomBranch(models.Model):
    """Operating unit / branch that lives inside a single company."""

    _name = "inom.branch"
    _description = "Company Branch / Unit"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "sequence, name"

    name = fields.Char(
        string="Branch Name", required=True, tracking=True, translate=True,
    )
    code = fields.Char(
        string="Branch Code", required=True, tracking=True,
        help="Short unique code used as a prefix for branch wise numbering.",
    )
    sequence = fields.Integer(string="Display Order", default=10)
    active = fields.Boolean(string="Active", default=True, tracking=True)
    color = fields.Integer(string="Color Index")

    company_id = fields.Many2one(
        comodel_name="res.company", string="Company", required=True,
        default=lambda self: self.env.company, tracking=True,
        index=True,
    )

    # Address block (kept self contained, no partner dependency).
    street = fields.Char(string="Street")
    street2 = fields.Char(string="Street 2")
    city = fields.Char(string="City")
    state_id = fields.Many2one(
        comodel_name="res.country.state", string="State",
        domain="[('country_id', '=?', country_id)]",
    )
    zip = fields.Char(string="ZIP")
    country_id = fields.Many2one(comodel_name="res.country", string="Country")
    email = fields.Char(string="Email")
    phone = fields.Char(string="Phone")
    mobile = fields.Char(string="Mobile")

    # Optional branch wise document numbering.
    use_own_sequence = fields.Boolean(
        string="Branch Wise Numbering",
        help="When enabled, a separate branch document number is assigned to "
             "every accounting document of this branch in addition to the "
             "standard Odoo number.",
    )
    sequence_id = fields.Many2one(
        comodel_name="ir.sequence", string="Document Sequence",
        copy=False,
        help="Sequence used to build the branch document number.",
    )

    user_ids = fields.Many2many(
        comodel_name="res.users", relation="inom_branch_allowed_users_rel",
        column1="branch_id", column2="user_id",
        string="Allowed Users",
        help="Users that are allowed to work in this branch.",
    )

    _sql_constraints = [
        ("inom_branch_code_company_uniq",
         "unique(code, company_id)",
         "Branch code must be unique per company."),
    ]

    @api.depends("name", "code")
    def _compute_display_name(self):
        for branch in self:
            if branch.code:
                branch.display_name = "[%s] %s" % (branch.code, branch.name or "")
            else:
                branch.display_name = branch.name or ""

    def _ensure_sequence(self):
        """Create an ir.sequence for the branch on demand."""
        self.ensure_one()
        if self.sequence_id:
            return self.sequence_id
        seq = self.env["ir.sequence"].sudo().create({
            "name": "Branch Document - %s" % (self.name or self.code),
            "code": "inom.branch.doc.%s" % (self.id,),
            "prefix": "%s/" % (self.code or "BR"),
            "padding": 5,
            "company_id": self.company_id.id,
        })
        self.sequence_id = seq.id
        return seq

    def next_document_number(self):
        """Return the next branch document number, or False if disabled."""
        self.ensure_one()
        if not self.use_own_sequence:
            return False
        seq = self._ensure_sequence()
        return seq.next_by_id()
