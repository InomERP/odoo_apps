{
    'name': 'Inom CRM Lead Automation',
    'version': '18.0.1.0',
    'category': 'Sales/CRM',
    'summary': 'Automatic email notification on CRM lead creation',
    'description': """
This module automatically sends an email notification whenever a new
CRM lead is created, ensuring instant communication with potential
customers and improving response time.

Key Features:
• Automatic email trigger on lead creation  
• Professional and customizable email template  
• Seamless integration with Odoo CRM  
• Eliminates manual follow-ups  
• Improves customer engagement and lead response time  
• Compatible with Odoo 18  

Ideal for businesses that want to automate lead communication and
enhance their CRM workflow.
""",
    'website': 'https://inomerp.in/',
    'author': 'InomERP',
    'depends': ['crm', 'mail'],
    'data': [
        'data/mail_template.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'application': True,
}

