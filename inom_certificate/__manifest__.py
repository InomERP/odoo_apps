{
    'name': 'University — Certificates',
    'summary': 'Certificate types, student requests, an issued register and '
               'public verification.',
    'description': """
University Management System — Certificates
===========================================
Bonafide, transfer, migration, conduct and character certificates: what a
student may request, who approves it, and what was actually issued.

Every issued certificate carries a verification code and the issued register is
append-only in practice — an employer checking a certificate that was quietly
edited afterwards is exactly the failure this register exists to prevent.
""",
    "version": "20.0.1.0.0",
    'category': 'Education',
    'license': 'LGPL-3',
    'depends': ['inom_portal', 'inom_student'],
    'data': [
        'security/ir.access.csv',
        'data/ir_sequence.xml',
        'data/certificate_type_data.xml',
        'reports/certificate.xml',
        'data/portal_data.xml',
        'data/notification_data.xml',
        'data/backend_menu_build.xml',
    ],
    'installable': True,
}
