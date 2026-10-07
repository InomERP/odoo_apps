import calendar
from datetime import datetime
from zoneinfo import ZoneInfo

from odoo import models, fields


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    birthday_wish_sent_date = fields.Date(
        string='Last Birthday Wish Sent On',
        copy=False,
        readonly=True,
        groups="hr.group_hr_user",
    )

    def _get_birthday_local_today(self):
        """Today's date in the employee's timezone (fallback: company tz, then UTC)."""
        self.ensure_one()
        tz_name = self.tz or self.company_id.tz or 'UTC'
        try:
            tz = ZoneInfo(tz_name)
        except Exception:
            tz = ZoneInfo('UTC')
        return datetime.now(tz).date()

    def _is_birthday_today(self, today):
        self.ensure_one()
        bday = self.birthday
        if not bday:
            return False
        if bday.month == today.month and bday.day == today.day:
            return True
        # Feb 29 birthdays are wished on Feb 28 in non-leap years
        return (
            bday.month == 2 and bday.day == 29
            and today.month == 2 and today.day == 28
            and not calendar.isleap(today.year)
        )

    def cron_send_birthday_wishes(self):
        template = self.env.ref(
            'inom_employee_birthday_wish.email_template_employee_birthday',
            raise_if_not_found=False
        )
        if not template:
            return

        employees = self.sudo().search([
            ('birthday', '!=', False),
            ('work_email', '!=', False),
        ])

        for emp in employees:
            today = emp._get_birthday_local_today()
            if emp.birthday_wish_sent_date == today or not emp._is_birthday_today(today):
                continue
            template.send_mail(emp.id, force_send=True)
            emp.birthday_wish_sent_date = today
