# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class SecondaryUomWizard(models.TransientModel):
    """Popup wizard to add a new Secondary UoM line to a product template.

    Matches the reference module popup: shows Secondary UoM, Secondary UoM Ratio,
    Product (readonly), and Ratio display (computed: '1 kg = 6.0 Units').
    """

    _name = "secondary.uom.wizard"
    _description = "Create Secondary UoM"

    product_tmpl_id = fields.Many2one(
        comodel_name="product.template",
        string="Product",
        required=True,
        readonly=True,
        ondelete="cascade",
    )
    uom_id = fields.Many2one(
        comodel_name="uom.uom",
        string="Secondary UoM",
        required=True,
        help="The secondary Unit of Measure to add for this product.",
    )
    ratio = fields.Float(
        string="Secondary UoM Ratio",
        default=0.0,
        digits="Product Unit of Measure",
        help="Conversion ratio: 1 secondary unit = ratio base units.",
    )
    ratio_display = fields.Char(
        string="Ratio",
        compute="_compute_ratio_display",
        help="Human-readable ratio e.g. '1 kg = 6.0 Units'",
    )

    @api.depends("uom_id", "ratio", "product_tmpl_id.uom_id")
    def _compute_ratio_display(self):
        for rec in self:
            if rec.uom_id and rec.ratio:
                base_uom = rec.product_tmpl_id.uom_id.name or ""
                rec.ratio_display = f"1 {rec.uom_id.name} = {rec.ratio} {base_uom}"
            else:
                rec.ratio_display = ""

    @api.constrains("ratio")
    def _check_ratio_positive(self):
        for rec in self:
            if rec.ratio <= 0:
                raise UserError(
                    _("The ratio to the base UoM must be strictly greater than zero.")
                )

    def _check_duplicate_uom(self):
        """Raise UserError if the same UoM already exists for this product."""
        self.ensure_one()
        existing = self.env["product.secondary.uom"].search([
            ("product_tmpl_id", "=", self.product_tmpl_id.id),
            ("uom_id", "=", self.uom_id.id),
        ], limit=1)
        if existing:
            raise UserError(
                _("Secondary UoM '%s' is already defined for this product.")
                % self.uom_id.name
            )

    def action_save_close(self):
        """Validate, create secondary UoM line, close dialog."""
        self.ensure_one()
        self._check_duplicate_uom()
        self.env["product.secondary.uom"].create({
            "product_tmpl_id": self.product_tmpl_id.id,
            "uom_id": self.uom_id.id,
            "ratio": self.ratio,
        })
        return {"type": "ir.actions.act_window_close"}

    def action_save_new(self):
        """Save and open fresh wizard for another UoM."""
        self.ensure_one()
        self._check_duplicate_uom()
        self.env["product.secondary.uom"].create({
            "product_tmpl_id": self.product_tmpl_id.id,
            "uom_id": self.uom_id.id,
            "ratio": self.ratio,
        })
        return {
            "type": "ir.actions.act_window",
            "name": _("Create Secondary UoM's"),
            "res_model": "secondary.uom.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_product_tmpl_id": self.product_tmpl_id.id,
            },
        }
