{
    'name': 'Inom Employee Birthday Wishes',
    'version': '1.0',
    'category': 'Human Resources',
    'summary': 'Automatically send birthday wishes emails to employees',
    'description': """
This module automatically sends birthday greeting emails to employees
using a scheduled cron job, helping organizations improve employee
engagement and workplace culture.

Key Features:
• Automatic birthday email sending via cron job  
• Personalized email templates with employee details  
• Runs daily without manual intervention  
• Works seamlessly with Odoo HR module  
• Compatible with Odoo 18  

Ideal for organizations that want to ensure timely and consistent
birthday greetings for their employees.
""",
    'website': 'https://inomerp.in/',
    'author': 'InomERP',
    'depends': ['hr', 'mail'],
    'data': [
        'data/birthday_email_template.xml',
        'data/birthday_cron.xml',
    ],
    'images': ['static/description/banner.png'],
    'license': 'LGPL-3',
    'installable': True,
    'application': True,
}
