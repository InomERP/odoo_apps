{
    'name': 'Inom Material Purchase Requisition',
    'version': '18.0.1.0.0',
    'category': 'Inventory/Purchase',
    'summary': 'Material Requisition workflow: Employee request, Manager/User approval, '
               'Internal Picking or Purchase Order fulfillment.',
    'description': """
Material Purchase Requisition
==============================
Employee-based material/product requisition workflow with department manager
and requisition user approval, internal picking or purchase order fulfillment.
""",
'keywords': [
    'Material Requisition',
    'Purchase Requisition',
    'Internal Picking',
    'Stock Requisition',
    'Employee Request',
    'Department Approval',
    'Manager Approval',
    'Material Request',
    'Inventory Requisition',
    'Procurement Request',
],
    'author': 'InomERP',
    'support': 'info@inomerp.in',
    'website': 'https://inomerp.in',
    'license': 'LGPL-3',
    'depends': [
        'hr',
        'stock',
        'purchase',
        'mail',
        'account',
    ],
    'data': [
        'security/security_groups.xml',
        'security/ir.model.access.csv',
        'security/record_rules.xml',
        'data/mail_template_data.xml',
        'data/material_requisition_sequence.xml',
        'report/requisition_report_template.xml',
        'report/requisition_report.xml',
        'views/rejection_wizard_views.xml',
        'views/material_requisition_views.xml',
        'views/hr_employee_views.xml',
        'views/hr_department_views.xml',
        'views/menu_views.xml',
    ],
    'images': ['static/description/banner.png'],
    'installable': True,
    'application': True,
}