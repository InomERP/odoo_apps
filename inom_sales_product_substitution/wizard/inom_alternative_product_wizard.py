# -*- coding: utf-8 -*-
import logging

from odoo import Command, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import format_datetime

from markupsafe import Markup

_logger = logging.getLogger(__name__)


def _inom_open_product_stock(product):
    """Return an act_window showing the location/warehouse-wise stock for a
    product, rendered as a popup.

    The native ``product.product.action_open_quants`` method is reused when
    available so the user sees the standard On Hand quants (grouped by
    location, which map to warehouses). A self-contained ``stock.quant``
    fallback is provided for robustness across editions.
    """
    product.ensure_one()
    action = False
    if hasattr(product, "action_open_quants"):
        action = product.action_open_quants()
    if isinstance(action, dict):
        action["target"] = "new"
        action.setdefault("name", "Stock by Location")
        return action
    return {
        "type": "ir.actions.act_window",
        "name": "Stock by Location",
        "res_model": "stock.quant",
        "view_mode": "list,form",
        "domain": [("product_id", "=", product.id)],
        "context": {
            "search_default_internal_loc": 1,
            "create": False,
            "edit": False,
        },
        "target": "new",
    }


class InomAlternativeProductWizard(models.TransientModel):
    _name = "inom.alternative.product.wizard"
    _description = "Alternative Product Replacement Wizard"

    sale_order_line_id = fields.Many2one(
        comodel_name="sale.order.line",
        string="Sales Order Line",
        required=True,
        ondelete="cascade",
    )
    order_id = fields.Many2one(
        comodel_name="sale.order",
        string="Sales Order",
        related="sale_order_line_id.order_id",
        readonly=True,
    )
    product_id = fields.Many2one(
        comodel_name="product.product",
        string="Original Product",
        related="sale_order_line_id.product_id",
        readonly=True,
    )
    product_uom_qty = fields.Float(
        string="Ordered Quantity",
        related="sale_order_line_id.product_uom_qty",
        readonly=True,
    )
    # ------------------------------------------------------------------
    # Original product header information (top stat row)
    # ------------------------------------------------------------------
    original_default_code = fields.Char(
        string="Internal Reference",
        related="product_id.default_code",
        readonly=True,
        help="Internal reference of the original product.",
    )
    original_list_price = fields.Float(
        string="Sales Price",
        related="product_id.list_price",
        readonly=True,
        help="Sales price of the original product.",
    )
    available_qty = fields.Float(
        string="Stock",
        readonly=True,
        help="On-hand quantity of the original product in the order "
             "warehouse (warehouse-scoped stock).",
    )
    original_general_stock = fields.Float(
        string="General Stock",
        readonly=True,
        help="On-hand quantity of the original product across every internal "
             "location of the company (company-wide stock).",
    )
    # ------------------------------------------------------------------
    # Replacement selection
    # ------------------------------------------------------------------
    allowed_alternative_ids = fields.Many2many(
        comodel_name="product.product",
        string="Allowed Alternatives",
        compute="_compute_allowed_alternative_ids",
        help="Technical field listing the configured alternatives. It scopes "
             "the 'Replacing Products' selection to valid substitutes only.",
    )
    replacing_product_id = fields.Many2one(
        comodel_name="product.product",
        string="Replacing Products",
        help="Alternative product that will replace the original product on "
             "the sales order line. The ordered quantity is preserved.",
    )
    line_ids = fields.One2many(
        comodel_name="inom.alternative.product.wizard.line",
        inverse_name="wizard_id",
        string="Alternative Products",
    )

    # ------------------------------------------------------------------
    # Computes
    # ------------------------------------------------------------------
    @api.depends("line_ids.product_id")
    def _compute_allowed_alternative_ids(self):
        for wizard in self:
            wizard.allowed_alternative_ids = wizard.line_ids.mapped("product_id")

    # ------------------------------------------------------------------
    # Defaults
    # ------------------------------------------------------------------
    @api.model
    def default_get(self, fields_list):
        values = super().default_get(fields_list)
        line_id = self.env.context.get("default_sale_order_line_id")
        if not line_id:
            return values

        order_line = self.env["sale.order.line"].browse(line_id)
        product = order_line.product_id
        warehouse = getattr(order_line.order_id, "warehouse_id", False)

        # Warehouse-scoped on-hand (Stock) and company-wide on-hand
        # (General Stock) for the original product.
        original = product.with_context(warehouse_id=warehouse.id) \
            if warehouse else product
        values["available_qty"] = original.qty_available if product else 0.0
        values["original_general_stock"] = product.qty_available \
            if product else 0.0

        wizard_lines = []
        alternatives = product._inom_get_effective_alternatives() \
            if product else self.env["product.product"]
        for alternative in alternatives:
            alt = alternative.with_context(warehouse_id=warehouse.id) \
                if warehouse else alternative
            wizard_lines.append(Command.create({
                "product_id": alternative.id,
                "qty_available": alt.qty_available,
                "general_stock": alternative.qty_available,
                "virtual_available": alt.virtual_available,
                "list_price": alternative.list_price,
                "uom_id": alternative.uom_id.id,
            }))
        values["line_ids"] = wizard_lines
        return values

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def action_view_original_stock(self):
        """Open the warehouse/location-wise stock of the original product."""
        self.ensure_one()
        if not self.product_id:
            raise UserError("No product is set on this line.")
        return _inom_open_product_stock(self.product_id)

    def action_replace(self):
        """Replace the order line product in place with the selected
        alternative.

        The product is changed on the original line so no duplicate line is
        created and the ordered quantity is preserved. Name, price, unit of
        measure and taxes are recomputed by the native sale order line
        computes. A controlled context relaxes the standard product-update
        guard so the replacement also works on confirmed lines; locked orders
        keep their native protection.

        The replacement source is the 'Replacing Products' selection. For
        backward compatibility, a single toggled wizard line is also accepted.
        """
        self.ensure_one()
        new_product = self.replacing_product_id
        if not new_product:
            selected = self.line_ids.filtered("selected")
            if len(selected) == 1:
                new_product = selected.product_id

        if not new_product:
            raise UserError(
                "Please select a replacement product before replacing."
            )

        order_line = self.sale_order_line_id
        original_product = order_line.product_id
        order = order_line.order_id
        replaced_qty = order_line.product_uom_qty

        order_line.with_context(inom_force_product_replace=True).write({
            "product_id": new_product.id,
        })

        self._inom_log_substitution(
            order, order_line, original_product, new_product, replaced_qty
        )

        _logger.info(
            "[INOM REPLACE] line %s replaced with product %s (qty kept: %s)",
            order_line.id,
            new_product.id,
            order_line.product_uom_qty,
        )
        return {"type": "ir.actions.act_window_close"}

    def _inom_log_substitution(self, order, order_line, original_product,
                               new_product, quantity):
        """Record the replacement in the audit log and post a chatter message.

        The history record is created with elevated rights so it behaves as an
        immutable audit trail (users keep read-only access). The chatter
        message is posted as the acting user so authorship is preserved.
        """
        self.ensure_one()
        history = self.env["inom.product.substitution.history"].sudo().create({
            "order_id": order.id,
            "order_line_id": order_line.id,
            "original_product_id": original_product.id,
            "replacement_product_id": new_product.id,
            "product_uom_qty": quantity,
            "user_id": self.env.user.id,
            "replacement_date": fields.Datetime.now(),
            "company_id": order.company_id.id,
        })

        body = Markup(
            "<p><strong>Product Substitution Completed</strong></p>"
            "<ul>"
            "<li><strong>Original Product:</strong> %s</li>"
            "<li><strong>Replacement Product:</strong> %s</li>"
            "<li><strong>Quantity:</strong> %s</li>"
            "<li><strong>Performed By:</strong> %s</li>"
            "<li><strong>Date:</strong> %s</li>"
            "</ul>"
        ) % (
            original_product.display_name,
            new_product.display_name,
            quantity,
            self.env.user.name,
            format_datetime(self.env, history.replacement_date),
        )
        order.message_post(body=body)
        return history


class InomAlternativeProductWizardLine(models.TransientModel):
    _name = "inom.alternative.product.wizard.line"
    _description = "Alternative Product Wizard Line"

    wizard_id = fields.Many2one(
        comodel_name="inom.alternative.product.wizard",
        string="Wizard",
        required=True,
        ondelete="cascade",
    )
    product_id = fields.Many2one(
        comodel_name="product.product",
        string="Alternative Product",
        required=True,
    )
    default_code = fields.Char(
        string="Internal Reference",
        related="product_id.default_code",
        readonly=True,
    )
    product_name = fields.Char(
        string="Product Name",
        related="product_id.name",
        readonly=True,
    )
    qty_available = fields.Float(string="Stock", readonly=True)
    general_stock = fields.Float(string="General Stock", readonly=True)
    virtual_available = fields.Float(string="Forecast", readonly=True)
    list_price = fields.Float(string="Sales Price", readonly=True)
    uom_id = fields.Many2one(
        comodel_name="uom.uom", string="Unit", readonly=True,
    )
    selected = fields.Boolean(string="Select")

    @api.onchange("selected")
    def _onchange_selected(self):
        """Enforce a single selection across the wizard lines."""
        if self.selected:
            others = self.wizard_id.line_ids.filtered(
                lambda line: line.id != self.id and line.selected
            )
            others.selected = False

    def action_view_stock(self):
        """Open the warehouse/location-wise stock of this alternative."""
        self.ensure_one()
        return _inom_open_product_stock(self.product_id)
