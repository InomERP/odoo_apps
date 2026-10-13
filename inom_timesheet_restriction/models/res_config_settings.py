from odoo import models, fields

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    restrict_backdate = fields.Boolean(
        string="Restrict Backdated Timesheets",
        help="If enabled, users will not be able to create or edit past timesheets.",
        config_parameter='inom_timesheet_restriction.restrict_backdate'
    )