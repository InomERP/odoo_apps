# -*- coding: utf-8 -*-
{
    'name': 'Inom Advanced DMS | Document Management, PDF Annotation & Versioning',
    'version': '17.0.1.0.0',
    'category': 'Productivity/Documents',
    'summary': 'All-in-one Document Management System for Odoo: workspaces, '
               'folders, drag and drop upload, PDF annotation, version control, '
               'approval requests, sharing, an analytics dashboard and a '
               'customer portal.',

    'description': """
Advanced Document Management System (DMS) for Odoo
==================================================
A complete, modern document management solution: organise files into
workspaces and folders, upload by drag and drop, annotate PDFs in the
browser, keep full version history, run approval requests, share securely
and monitor everything from an analytics dashboard.

Key Features
------------

* Workspaces, folders and tags for clean organisation
* Drag and drop multi-file upload with live progress
* In-browser PDF annotator (highlight, notes, shapes, drawings)
* Document versioning with full history
* Approval / review requests and sharing wizards
* Favourites and trash with auto-cleanup
* Real-time analytics dashboard with KPIs and charts
* Customer portal access

Built for Heavy Repositories
-----------------------------------------

* Bulk actions framework: move, group, reorder, tag, change status,
  archive/restore, recycle bin, permanent delete and ZIP download - all
  driven from the multi-selection of the list and kanban views
* Logical document groups (relational only - files are never duplicated)
* Persisted document ordering with a drag handle and batch renumbering
* Alternative presentations: list, grid/card and group board views
* Full post-upload management: rename, move, replace file with automatic
  versioning, edit metadata, tags, archive, delete and download
* Search panel, extra filters and group-bys for fast document discovery
* File size tracked as metadata so listings never load binary content
* Database indexes on the columns the DMS filters and groups on
""",

    'author': 'InomERP',
    'maintainer': 'InomERP',
    'company': 'InomERP',
    'website': 'https://www.inomerp.in',
    'support': 'support@inomerp.in',
    'license': 'OPL-1',
   

    'depends': [
        'base',
        'mail',
        'web',
        'website',
        'portal',
    ],

    'data': [

        # SECURITY
        'security/document_security.xml',
        'security/ir.model.access.csv',

        # DATA
        'data/sequence.xml',
        'data/document_expiry_cron.xml',
        'data/document_trash_cron.xml',
        'views/res_config_settings_views.xml',

        # MAIN VIEWS
        'views/document_workspace_views.xml',
        'views/document_folder_views.xml',
        'views/document_tag_views.xml',
        'views/document_annotation_views.xml',
        'views/document_category_views.xml',
        'views/document_group_views.xml',
        'views/document_document_views.xml',
        'views/document_dashboard_views.xml',

        # OWL client actions (analytics dashboard + drag&drop upload)
        'views/document_dashboard_action.xml',

        # WIZARDS
        'views/document_wizard_views.xml',
        'wizard/document_share_wizard_views.xml',
        'wizard/document_request_wizard_views.xml',
        'wizard/document_bulk_wizard_views.xml',

        # REQUESTS
        'views/document_request_views.xml',

        # PORTAL
        'views/portal_templates.xml',

        # MENU (LAST)
        'views/document_menu.xml',
    ],

    'assets': {
        'web.assets_backend': [
            'inom_advance_dms/static/src/css/pdf_annotator.css',
            'inom_advance_dms/static/src/js/pdf_annotator.js',
            'inom_advance_dms/static/src/js/pdf_annotator_action.js',
            # Analytics dashboard (OWL)
            'inom_advance_dms/static/src/css/dashboard.css',
            'inom_advance_dms/static/src/js/dashboard/dashboard.js',
            'inom_advance_dms/static/src/xml/dashboard.xml',
            'inom_advance_dms/static/src/js/doc_popup.js',
            'inom_advance_dms/static/src/xml/doc_popup.xml',
            # Drag & drop upload (OWL)
            'inom_advance_dms/static/src/css/document_grid.css',
            'inom_advance_dms/static/src/js/views/view_memory.js',
            'inom_advance_dms/static/src/css/upload_dropzone.css',
            'inom_advance_dms/static/src/js/upload/upload_dropzone.js',
            'inom_advance_dms/static/src/xml/upload_dropzone.xml',
            # Document quick-action popup
        ],
    },

    'images': [
        'static/description/banner.png',
    ],

    'post_init_hook': 'post_init_hook',

    'application': True,
    'installable': True,
    'auto_install': False,
}
