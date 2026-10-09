{
    'name': 'University — Hostel',
    'summary': 'Blocks, room inventory, allocations, mess and the visitor register.',
    'description': """
University Management System — Hostel
=====================================
Residential blocks, rooms, who is allocated where, and the visitor register.

Occupancy is computed from active allocations, never a stored counter. A
counter drifts the first time an allocation is archived out of order, and the
warden finds out when two students arrive at the same bed.
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
