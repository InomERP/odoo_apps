# -*- coding: utf-8 -*-
{
    'name': 'Inom Quick Sale',

    'version': '19.0.1.0.0',

    'summary': 'Inom Quick Sale - Auto Delivery, Auto Invoice, Returns and Stock Validation',

    'description': """
Quick Sale Automation
========================

This module provides a complete Quick Sale Automation workflow
in Odoo with automatic delivery validation, invoice generation,
stock validation, and return management.

Main Features:
--------------
- Create Quick Sale Orders
- Automatic Delivery Validation
- Automatic Invoice Generation
- Automatic Workflow Synchronization
- Auto Cancel Related Invoice
- Real-Time Stock Validation
- Product Return Management
- Reverse Transfer Handling
- User & Manager Access Rights
- Custom Quick Sale Sequence
- Warehouse Stock Automation
- Smart Inventory Management

Workflow Features:
------------------
- Quick Sale Order Creation
- One Click Sales Processing
- Automatic Stock Transfer
- Delivery Auto Validation
- Invoice Auto Creation
- Sales & Invoice Synchronization
- Return Receipt Validation
- Inventory Quantity Updates

Security Features:
------------------
- Quick Sale User Access
- Quick Sale Manager Access
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

