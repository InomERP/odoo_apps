# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


class UnivTransportSubscription(models.Model):
    _name = "univ.transport.subscription"
    _description = "Transport Subscription"
    _inherit = ["mail.thread"]
    _order = "create_date desc, id desc"

    name = fields.Char(string="Pass No.", copy=False, readonly=True,
                       default=lambda self: self.env._("New"))
    student_id = fields.Many2one(comodel_name="univ.student", string="Student",
                                 required=True, index=True, tracking=True)
    route_id = fields.Many2one(comodel_name="univ.transport.route",
                               string="Route", required=True, index=True)
    stop_id = fields.Many2one(comodel_name="univ.transport.stop", string="Stop",
                              required=True,
                              domain="[('route_id', '=', route_id)]")
    vehicle_id = fields.Many2one(comodel_name="univ.transport.vehicle",
                                 string="Vehicle", related="route_id.vehicle_id",
                                 store=True)
    fee_amount = fields.Monetary(string="Fee", related="route_id.fee_amount",
                                 store=True)
    fee_invoice_id = fields.Many2one(comodel_name="univ.fee.invoice",
                                     string="Fee Invoice", readonly=True)
    currency_id = fields.Many2one(
        comodel_name="res.currency", related="route_id.currency_id")
    valid_from = fields.Date(string="Valid From",
                             default=fields.Date.context_today)
    valid_to = fields.Date(string="Valid To")
    state = fields.Selection(
        selection=[
            ("requested", "Requested"),
            ("mapped", "Stop Mapped"),
            ("fee_added", "Fee Added"),
            ("issued", "Pass Issued"),
            ("cancelled", "Cancelled"),
        ], string="Status", default="requested", required=True, tracking=True)
    company_id = fields.Many2one(
        comodel_name="res.company", string="Company",
        default=lambda self: self.env.company, index=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("name") or vals["name"] in (self.env._("New"), "New"):
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "univ.transport.subscription") or "TRN-P/0001"
        return super().create(vals_list)

    @api.constrains("route_id", "state")
    def _check_capacity(self):
        for sub in self.filtered(lambda s: s.state in ("fee_added", "issued")):
            route = sub.route_id
            cap = route.vehicle_id.capacity or 0
            used = self.search_count([
                ("route_id", "=", route.id),
                ("state", "in", ("fee_added", "issued"))])
            if cap and used > cap:
                raise ValidationError(self.env._(
                    "Route %s is at full capacity (%s seats).",
                    route.name, cap))

    def action_map_stop(self):
        for sub in self:
            if not sub.stop_id:
                raise UserError(self.env._("Select a boarding stop."))
            sub.state = "mapped"

    def action_add_fee(self):
        """Inject the route-wise transport fee into the student ledger."""
        for sub in self:
            if sub.state not in ("requested", "mapped"):
                raise UserError(self.env._("Map the stop first."))
            head = sub.route_id.fee_head_id
            if not head:
                raise UserError(self.env._(
                    "Configure a Fee Head on the route."))
            if sub.fee_amount and sub.fee_amount > 0 and not sub.fee_invoice_id:
                invoice = self.env["univ.fee.invoice"].create_service_charge(
                    sub.student_id, head, sub.fee_amount,
                    label=self.env._("Transport: %s", sub.route_id.name))
                sub.fee_invoice_id = invoice.id
            sub.state = "fee_added"

    def action_issue_pass(self):
        for sub in self:
            if sub.state != "fee_added":
                raise UserError(self.env._("Add the fee before issuing the pass."))
            sub.state = "issued"

    def action_cancel(self):
        self.write({"state": "cancelled"})
