{
    'name': 'University — Learning',
    'summary': 'Online courses, lessons, assignments and submissions.',
    'description': """
University Management System — Learning
=======================================
Course content, lessons, assignments and graded submissions.

Draft courses are invisible to students, enforced by a record rule rather than
a filter on the list: a student who reconstructs the API call gets the same
answer the screen would give them.

Where the client wants SCORM or certification, website_slides is the better
base — it brings its own portal UI, which then has to be re-skinned to match
the design system. Worth pricing before choosing.
""",
    "version": "20.0.1.0.0",
    'category': 'Education',
    'license': 'LGPL-3',
    'depends': ['inom_portal', 'inom_student', 'inom_faculty'],
    'data': [
        'data/portal_data.xml',
        'data/backend_menu_build.xml',
        'security/ir.access.csv',
    ],
    'installable': True,
}
