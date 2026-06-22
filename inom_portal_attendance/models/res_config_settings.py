# -*- coding: utf-8 -*-
from odoo import fields, models

# Config parameter keys used by this module. Keeping them in one place avoids
# typos between the settings model, the controller and the templates.
PARAM_ENABLED = "inom_portal_attendance.enabled"
PARAM_TIME_FORMAT = "inom_portal_attendance.time_format"
PARAM_CALC_METHOD = "inom_portal_attendance.calc_method"


class ResConfigSettings(models.TransientModel):
    """Add the portal attendance options to the general settings.

    The values are persisted as ``ir.config_parameter`` records, so no field is
    added to any existing Odoo model and the standard configuration is left
    untouched.
    """

    _inherit = "res.config.settings"

    inom_portal_attendance_enabled = fields.Boolean(
        string="Portal Attendance",
        config_parameter=PARAM_ENABLED,
        help="Allow employees to check in, check out and review their "
             "attendance from the website portal.",
    )
    inom_portal_attendance_time_format = fields.Selection(
        selection=[
            ("12", "12 Hours"),
            ("24", "24 Hours"),
        ],
        string="Portal Time Format",
        default="24",
        config_parameter=PARAM_TIME_FORMAT,
        help="Time format used to display check-in and check-out values on "
             "the portal.",
    )
    inom_portal_attendance_calc_method = fields.Selection(
        selection=[
            ("odoo", "Odoo Flow (Worked & Extra Hours)"),
            ("portal_avg", "Portal Based (Average Hours per Day)"),
        ],
        string="Extra Hours Calculation",
        default="odoo",
        config_parameter=PARAM_CALC_METHOD,
        help="How the extra hours shown on the portal are computed:\n"
             "- Odoo Flow: reuse the native validated extra hours.\n"
             "- Portal Based: worked hours minus the average hours per day of "
             "the employee work schedule.",
    )
