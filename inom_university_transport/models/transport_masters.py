# -*- coding: utf-8 -*-
from odoo import _, api, fields, models


class UnivTransportDriver(models.Model):
    _name = "univ.transport.driver"
    _description = "Driver / Conductor"
    _order = "name"

    name = fields.Char(string="Name", required=True)
    partner_id = fields.Many2one(comodel_name="res.partner", string="Contact")
    role = fields.Selection(
        selection=[("driver", "Driver"), ("conductor", "Conductor")],
        string="Role", default="driver", required=True)
    phone = fields.Char(string="Phone")
    license_no = fields.Char(string="License No.")
    license_expiry = fields.Date(string="License Expiry")
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        comodel_name="res.company", string="Company",
        default=lambda self: self.env.company, index=True)


class UnivTransportVehicle(models.Model):
    _name = "univ.transport.vehicle"
    _description = "Vehicle"
    _inherit = ["mail.thread"]
    _order = "regno"

    name = fields.Char(string="Vehicle", compute="_compute_name", store=True)
    regno = fields.Char(string="Registration No.", required=True, tracking=True)
    vehicle_type = fields.Selection(
        selection=[("bus", "Bus"), ("van", "Van"), ("car", "Car")],
        string="Type", default="bus", required=True)
    capacity = fields.Integer(string="Seating Capacity", default=40)
    driver_id = fields.Many2one(comodel_name="univ.transport.driver",
                                string="Driver")
    insurance_expiry = fields.Date(string="Insurance Expiry", tracking=True)
    fitness_expiry = fields.Date(string="Fitness Expiry", tracking=True)
    permit_expiry = fields.Date(string="Permit Expiry", tracking=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        comodel_name="res.company", string="Company",
        default=lambda self: self.env.company, index=True)

    _sql_constraints = [
        ("regno_uniq", "unique(regno, company_id)",
         "Registration number must be unique."),
    ]

    @api.depends("regno", "vehicle_type")
    def _compute_name(self):
        for vehicle in self:
            vehicle.name = "%s (%s)" % (vehicle.regno or "", vehicle.vehicle_type)

    @api.model
    def _cron_document_expiry_alert(self):
        """Notify on vehicle documents expiring within 30 days."""
        from datetime import timedelta
        today = fields.Date.context_today(self)
        horizon = today + timedelta(days=30)
        for vehicle in self.search([]):
            for field_name, label in (
                ("insurance_expiry", "Insurance"),
                ("fitness_expiry", "Fitness"),
                ("permit_expiry", "Permit"),
            ):
                expiry = vehicle[field_name]
                if expiry and today <= expiry <= horizon:
                    vehicle.message_post(body=_(
                        "%(doc)s for %(veh)s expires on %(date)s.",
                        doc=label, veh=vehicle.regno, date=expiry))


class UnivTransportRoute(models.Model):
    _name = "univ.transport.route"
    _description = "Transport Route"
    _inherit = ["mail.thread"]
    _order = "name"

    name = fields.Char(string="Route", required=True, tracking=True)
    code = fields.Char(string="Code")
    vehicle_id = fields.Many2one(comodel_name="univ.transport.vehicle",
                                 string="Vehicle")
    driver_id = fields.Many2one(comodel_name="univ.transport.driver",
                                string="Driver",
                                related="vehicle_id.driver_id", store=True)
    fee_amount = fields.Monetary(string="Route Fee")
    fee_head_id = fields.Many2one(comodel_name="univ.fee.head",
                                  string="Transport Fee Head")
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        default=lambda self: self.env.company.currency_id)
    stop_ids = fields.One2many(comodel_name="univ.transport.stop",
                               inverse_name="route_id", string="Stops")
    subscription_ids = fields.One2many(
        comodel_name="univ.transport.subscription", inverse_name="route_id",
        string="Subscriptions")
    seats_used = fields.Integer(string="Seats Used", compute="_compute_seats")
    seats_available = fields.Integer(string="Seats Available",
                                     compute="_compute_seats")
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        comodel_name="res.company", string="Company",
        default=lambda self: self.env.company, index=True)

    @api.depends("subscription_ids.state", "vehicle_id.capacity")
    def _compute_seats(self):
        for route in self:
            used = len(route.subscription_ids.filtered(
                lambda s: s.state in ("fee_added", "issued")))
            route.seats_used = used
            cap = route.vehicle_id.capacity or 0
            route.seats_available = max(cap - used, 0)


class UnivTransportStop(models.Model):
    _name = "univ.transport.stop"
    _description = "Route Stop"
    _order = "route_id, sequence"

    name = fields.Char(string="Stop", required=True)
    route_id = fields.Many2one(comodel_name="univ.transport.route",
                               string="Route", required=True, ondelete="cascade",
                               index=True)
    sequence = fields.Integer(string="Sequence", default=10)
    pickup_time = fields.Float(string="Pickup Time")
    latitude = fields.Float(string="Latitude", digits=(10, 7))
    longitude = fields.Float(string="Longitude", digits=(10, 7))
    company_id = fields.Many2one(
        comodel_name="res.company", string="Company",
        related="route_id.company_id", store=True, index=True)
