# -*- coding: utf-8 -*-
from odoo import fields, models


CERT_TYPES = [
    ("bonafide", "Bonafide Certificate"),
    ("character", "Character Certificate"),
    ("transfer", "Transfer Certificate"),
    ("migration", "Migration Certificate"),
    ("completion", "Completion Certificate"),
    ("degree", "Degree Certificate"),
    ("id_card", "ID Card"),
]


class UnivCertificateTemplate(models.Model):
    _name = "univ.certificate.template"
    _description = "Certificate Template"
    _order = "name"

    name = fields.Char(string="Template", required=True)
    cert_type = fields.Selection(selection=CERT_TYPES, string="Type",
                                 required=True, default="bonafide")
    prefix = fields.Char(string="Number Prefix", default="CERT/")
    body_html = fields.Html(string="Body",
                            help="Use placeholders like {student}, {program}, "
                                 "{batch}, {date}, {number}.")
    signatory = fields.Char(string="Signatory")
    signatory_designation = fields.Char(string="Designation")
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        comodel_name="res.company", string="Company",
        default=lambda self: self.env.company, index=True)
