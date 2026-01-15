from odoo import models, fields
from datetime import date

class HrEmployee(models.Model):
    _inherit = 'hr.employee'


    def cron_send_birthday_wishes(self):
        today = date.today()

        employees = self.sudo().search([
            ('birthday', '!=', False),
            ('work_email', '!=', False),
        ])

        template = self.env.ref(
            'inom_employee_birthday_wish.email_template_employee_birthday',
            raise_if_not_found=False
        )

        if not template:
            return

        for emp in employees:
            if (
                emp.birthday
                and emp.birthday.month == today.month
                and emp.birthday.day == today.day
            ):
                template.send_mail(emp.id, force_send=True)

