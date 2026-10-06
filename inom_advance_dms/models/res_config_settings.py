from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    edm_trash_auto_delete_days = fields.Integer(
        string="Recycle Bin Auto Delete Days",
        config_parameter='edm.trash_auto_delete_days',
        default=30
    )