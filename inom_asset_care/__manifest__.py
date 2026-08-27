# -*- coding: utf-8 -*-
{
    'name': 'Inom AssetCare - Complete Asset & Maintenance Suite',
    'version': '17.0.1.0.0',
    'category': 'Operations/Maintenance',
    'summary': 'Asset registry, preventive maintenance, work orders, safety permits, '
               'inspections, meters with IoT ingestion, depreciation and WhatsApp alerts '
               '- full EAM suite for Odoo Community',
    'description': """
AssetCare - Complete Asset & Maintenance Suite
==============================================
* Asset registry with parent/child hierarchy, categories and location tree
* QR coded asset labels with printable PDF
* Custody management and transfer workflow with approval
* Maintenance requests and full work order lifecycle
* Labor, spare parts (real stock moves) and checklist tracking on work orders
* Permit to Work and LOTO safety layer that blocks unsafe work orders
* Inspection templates and asset inspections with auto follow-up requests
* Asset meters with manual readings and token secured IoT REST endpoint
* Preventive maintenance plans (time and meter based) with cron automation
* Straight line and declining balance depreciation engine for Community
* WhatsApp deep-link notifications for transfers and work orders
* MTBF / MTTR / Health score analytics, pivot and graph reporting
""",
    'author': 'InomERP',
    'website': 'https://inomerp.in',
    'license': 'OPL-1',
    'depends': ['base', 'mail', 'hr', 'stock', 'portal'],
    'data': [
        'security/security_groups.xml',
        'security/ir.model.access.csv',
        'data/sequence_data.xml',
        'data/cron_data.xml',
        'views/asset_category_views.xml',
        'views/asset_location_views.xml',
        'views/asset_views.xml',
        'views/asset_transfer_views.xml',
        'views/maintenance_request_views.xml',
        'views/work_permit_views.xml',
        'views/work_order_views.xml',
        'views/inspection_views.xml',
        'views/meter_views.xml',
        'views/maintenance_plan_views.xml',
        'views/depreciation_views.xml',
        'views/res_config_settings_views.xml',
        'wizard/mass_transfer_wizard_views.xml',
        'report/asset_label_report.xml',
        'report/work_order_report.xml',
        'views/menus.xml',
    ],
  'images': [
        # 'static/description/banner.png',
        'static/description/banner.gif',
    ],

    'installable': True,
    'application': True,
    'auto_install': False,
}
