from odoo import fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    toggle_color = fields.Char(
        string="Toggle Color",
        config_parameter='inom_lvm.toggle_color',
        default="#875A7B"
    )

    header_color = fields.Char(
        string="LVM Header Color",
        config_parameter='inom_lvm.header_color',
        default="#875A7B"
    )

    header_text_color = fields.Char(
        string="Header Text Color",
        config_parameter='inom_lvm.header_text_color',
        default="#FFFFFF"
    )
    enable_serial_number = fields.Boolean(
        string="Enable Serial Number",
        config_parameter="inom_lvm.enable_serial_number",
    )