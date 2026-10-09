{
    'name': 'University — Library',
    'summary': 'Catalogue at title and copy level, circulation, fines and members.',
    'description': """
University Management System — Library
======================================
Titles, physical copies, issue and return, and overdue fines.

Copies are their own model rather than a count on the title. Barcodes are per
copy, not per book, and a library that tracks only "4 available" cannot tell
you which four or where they are.
""",
    "version": "20.0.1.0.0",
    'category': 'Education',
    'license': 'LGPL-3',
    'depends': [],
    'data': [
        'data/portal_data.xml',
        'data/backend_menu_build.xml',
        'security/ir.access.csv',
    ],
    'installable': True,
}
