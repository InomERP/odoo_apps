from odoo import models, api, fields, _
from odoo.exceptions import UserError

class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    @api.model_create_multi
    def create(self, vals_list):
        restrict = self.env['ir.config_parameter'].sudo().get_param(
            'inom_timesheet_restriction.restrict_backdate'
        )

        if restrict in ['True', True]:
            today = fields.Date.today()

            for vals in vals_list:
                entry_date = vals.get('date')

                if entry_date:
                    entry_date = fields.Date.to_date(entry_date)
                    if entry_date < today:
                        raise UserError(_("You cannot fill past timesheets. if you want to fill past timesheet so please mail on info@inomerp.in"))

        return super().create(vals_list)

    def write(self, vals):
        restrict = self.env['ir.config_parameter'].sudo().get_param(
            'inom_timesheet_restriction.restrict_backdate'
        )

        if restrict in ['True', True]:
            if 'date' in vals:
                entry_date = fields.Date.to_date(vals.get('date'))
                today = fields.Date.today()

                # 🚫 Block editing to past date
                if entry_date < today:
                    raise UserError(_("You cannot modify timesheet to a past date."))

        return super().write(vals)