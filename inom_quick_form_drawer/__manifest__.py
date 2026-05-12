{
    'name': 'Inom Quick Form Drawer',
    'version': '17.0.1.0.7',
    'category': 'Productivity',
    'summary': 'Eye icon on every list row that opens a right-side drawer with the full form view (view + edit).',
    'description': """
Quick Form Drawer
=================

Adds a generic eye-icon button to every row in every list view across Odoo 19.
Clicking the icon slides a drawer in from the right showing that record's
form view. The form is fully functional inside the drawer:

* All field widgets render normally
* Save / discard work
* Statusbar buttons and header actions work
* Chatter, smart buttons and attachments are all available

No model changes, no XML data records - purely a frontend extension that
applies to every list view automatically.

Features
--------
* Generic: works on every model's list view out of the box
* Smooth right-side slide-in drawer with backdrop
* ESC key and backdrop click to close
* Fully editable form view inside the drawer
* Lightweight (no Python logic, only JS/SCSS assets)

Technical
---------
* Patches ``ListRenderer`` (JS) and uses OWL lifecycle hooks to inject
  an eye-icon column into the rendered list table DOM. This is robust
  against Odoo template changes between versions.
* Reactive ``record_drawer`` service holds the open state.
* OWL ``RecordDrawer`` component registered as a ``main_components`` entry.
* Embeds Odoo's standard ``<View>`` component for the form.

Compatibility
-------------
Odoo 19.0 Community and Enterprise.
""",
    'author': 'InomERP',
    'maintainer': 'InomERP Pvt Ltd',
    'website': 'https://inomerp.in',
    'support': 'info@inomerp.in',
    'license': 'LGPL-3',
    'depends': ['web'],
    'data': [],
    'assets': {
        'web.assets_backend': [
            'inom_quick_form_drawer/static/src/**/*',
        ],
    },
    'images': [
        'static/description/banner.png',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'price': 0.00,
    'currency': 'EUR',
}
