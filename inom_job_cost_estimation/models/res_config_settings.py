# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    inom_approval_threshold = fields.Float(
        string='Approval Threshold',
        config_parameter='inom_job_cost_estimation.approval_threshold',
        help='Estimates whose total exceeds this amount can only be approved by a '
             'Job Costing Manager. Set 0 to disable the threshold.')

    inom_material_product_id = fields.Many2one(
        'product.product', string='Material Fallback Product',
        config_parameter='inom_job_cost_estimation.material_product_id',
        domain=[('sale_ok', '=', True)],
        help='Product used on the quotation for material lines that have no '
             'product of their own.')
    inom_labour_product_id = fields.Many2one(
        'product.product', string='Manpower Product',
        config_parameter='inom_job_cost_estimation.labour_product_id',
        domain=[('sale_ok', '=', True)],
        help='Product used on the quotation to carry manpower / labour cost.')
    inom_approval_threshold_high = fields.Float(
        string='Director Threshold',
        config_parameter='inom_job_cost_estimation.approval_threshold_high',
        help='Estimates above this amount need a Job Costing Director to '
             'approve. Leave 0 to require only a Manager above the first '
             'threshold.')
    inom_rounding_step = fields.Float(
        string='Round Final Price To',
        config_parameter='inom_job_cost_estimation.rounding_step',
        help='Round the final price to the nearest multiple of this amount. '
             'Set 0 to disable. The difference is shown as a separate '
             'Rounding line, never hidden inside the price.')

    inom_equipment_product_id = fields.Many2one(
        'product.product', string='Equipment Product',
        config_parameter='inom_job_cost_estimation.equipment_product_id',
        domain=[('sale_ok', '=', True)],
        help='Product used on the quotation to carry equipment cost.')
    inom_overhead_product_id = fields.Many2one(
        'product.product', string='Indirect Cost Product',
        config_parameter='inom_job_cost_estimation.overhead_product_id',
        domain=[('sale_ok', '=', True)],
        help='Product used on the quotation to carry indirect / overhead cost.')
