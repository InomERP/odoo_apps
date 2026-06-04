# -*- coding: utf-8 -*-
{
    'name': 'Inom Instant Sales Automation | Auto Invoice | Auto Delivery',

    'version': '19.0.1.0.0',

    'summary': 'Instant Sales Automation with Auto Delivery, Auto Invoice, Returns and Stock Validation',

    'description': """
Instant Sales Automation
========================

This module provides a complete Instant Sales Automation workflow
in Odoo with automatic delivery validation, invoice generation,
stock validation, and return management.

Main Features:
--------------
- Create Instant Sales Orders
- Automatic Delivery Validation
- Automatic Invoice Generation
- Automatic Workflow Synchronization
- Auto Cancel Related Invoice
- Real-Time Stock Validation
- Product Return Management
- Reverse Transfer Handling
- User & Manager Access Rights
- Custom Instant Sales Sequence
- Warehouse Stock Automation
- Smart Inventory Management

Workflow Features:
------------------
- Instant Sales Order Creation
- One Click Sales Processing
- Automatic Stock Transfer
- Delivery Auto Validation
- Invoice Auto Creation
- Sales & Invoice Synchronization
- Return Receipt Validation
- Inventory Quantity Updates

Security Features:
------------------
- Instant Sale User Access
- Instant Sale Manager Access
- Role Based Permissions

Compatible with Odoo 19 Community Edition.
""",

    'category': 'Sales',

    'website': 'https://inomerp.in',

    'author': 'InomERP',

    'depends': [
        'sale_management',
        'stock',
        'account',
        'sale_stock',
    ],

    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'views/res_config_settings_views.xml',
        'views/sale_order_views.xml',
    ],

    'images': [
        'static/description/banner.png'
    ],

    'installable': True,

    'application': False,

    'auto_install': False,

    'license': 'LGPL-3',
}

