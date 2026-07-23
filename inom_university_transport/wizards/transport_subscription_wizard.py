# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class UnivTransportSubscriptionWizard(models.TransientModel):
    _name = "univ.transport.subscription.wizard"
    _description = "Create Transport Subscription"

    student_id = fields.Many2one(comodel_name="univ.student", string="Student",
                                 required=True)
    route_id = fields.Many2one(comodel_name="univ.transport.route",
                               string="Route", required=True)
    stop_id = fields.Many2one(comodel_name="univ.transport.stop", string="Stop",
                              required=True,
                              domain="[('route_id', '=', route_id)]")
    valid_from = fields.Date(string="Valid From",
                             default=fields.Date.context_today)
    valid_to = fields.Date(string="Valid To")
    add_fee = fields.Boolean(string="Add Fee Now", default=True)

    @api.onchange("route_id")
    def _onchange_route(self):
        self.stop_id = False

    def action_create(self):
        self.ensure_one()
        route = self.route_id
        if route.vehicle_id and route.seats_available <= 0:
            raise UserError(_("Route %s has no seats available.",
                                       route.name))
        sub = self.env["univ.transport.subscription"].create({
            "student_id": self.student_id.id,
            "route_id": route.id,
            "stop_id": self.stop_id.id,
            "valid_from": self.valid_from,
            "valid_to": self.valid_to,
        })
        sub.action_map_stop()
        if self.add_fee:
            sub.action_add_fee()
        return {
            "type": "ir.actions.act_window",
            "res_model": "univ.transport.subscription",
            "res_id": sub.id,
            "view_mode": "form",
            "target": "current",
        }
