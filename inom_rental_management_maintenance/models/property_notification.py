from dateutil.relativedelta import relativedelta

from odoo import api, fields, models


class PropertyNotification(models.AbstractModel):
    _inherit = 'property.notification'

    @api.model
    def _cron_send_notifications(self):
        super()._cron_send_notifications()
        self._notify_scheduled_maintenance()

    @api.model
    def _notify_scheduled_maintenance(self):
        """ Remind the responsible person of property work scheduled soon. A request is reminded
        again only if it is rescheduled. """
        now = fields.Datetime.now()
        Request = self.env['maintenance.request'].sudo()
        for company in self.env['res.company'].sudo().search([]):
            days = company.rental_maintenance_reminder_days
            if days <= 0:
                continue
            requests = Request.search([
                ('company_id', '=', company.id),
                ('property_id', '!=', False),
                ('archive', '=', False),
                ('stage_id.done', '=', False),
                ('user_id', '!=', False),
                ('schedule_date', '>=', now),
                ('schedule_date', '<=', now + relativedelta(days=days)),
            ]).filtered(lambda r: r.schedule_reminder_date != r.schedule_date)
            for request in requests:
                self._todo(
                    request, request.user_id,
                    self.env._("Scheduled maintenance at %(property)s on %(date)s",
                               property=request.property_id.display_name,
                               date=fields.Datetime.context_timestamp(request, request.schedule_date).strftime('%Y-%m-%d %H:%M')),
                    deadline=request.schedule_date.date(),
                )
                request.schedule_reminder_date = request.schedule_date


class PropertyDashboard(models.AbstractModel):
    _inherit = 'property.dashboard'

    @api.model
    def _calendar_extra_events(self, env, companies, today, until):
        """ Property maintenance scheduled in the coming days, one entry per day. """
        events = super()._calendar_extra_events(env, companies, today, until)
        company_domain = [('company_id', 'in', companies.ids)]
        domain = company_domain + [
            ('property_id', '!=', False), ('stage_id.done', '=', False),
            ('schedule_date', '>=', fields.Datetime.to_datetime(today)),
            ('schedule_date', '<', fields.Datetime.to_datetime(until + relativedelta(days=1))),
        ]
        for day, number, ids in env['maintenance.request']._read_group(
                domain, ['schedule_date:day'], ['property_id:count_distinct', 'id:array_agg']):
            events.append(self._calendar_event(
                day, 'maintenance', self.env._("Maintenance"), number, self.env._("Scheduled"), 'info',
                self._action(self.env._("Scheduled Maintenance"), 'maintenance.request', [('id', 'in', ids)])))
        return events
