# -*- coding: utf-8 -*-
from odoo import fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    pos_iml_enable_lot_scanning = fields.Boolean(related='pos_config_id.iml_enable_lot_scanning', readonly=False)
    pos_iml_enable_lot_popup = fields.Boolean(related='pos_config_id.iml_enable_lot_popup', readonly=False)
    pos_iml_strict_qty_validation = fields.Boolean(related='pos_config_id.iml_strict_qty_validation', readonly=False)
    pos_iml_check_duplicate_serial = fields.Boolean(related='pos_config_id.iml_check_duplicate_serial', readonly=False)
    pos_iml_allow_create_lot = fields.Boolean(related='pos_config_id.iml_allow_create_lot', readonly=False)
    pos_iml_allow_offline_lot_create = fields.Boolean(related='pos_config_id.iml_allow_offline_lot_create', readonly=False)
    pos_iml_print_lot_on_receipt = fields.Boolean(related='pos_config_id.iml_print_lot_on_receipt', readonly=False)