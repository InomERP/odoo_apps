{
    'name': 'Inom Security User Roles',
    'version': '20.0.1.1.0',
    'category': 'Tools',
        'summary': 'User Roles | Access Rights | Permission Management | Role Based Access Control | RBAC | User Groups | Security Roles | Assign Roles to Users | Manage Permissions | Role Management',    'description': """
    Odoo User Roles | Role Based Access Control | RBAC
    =====================================================
    * Assign Roles to Users
    * Manage Permissions through Roles
    * Role Based Access Control (RBAC)
    * User Group Management
    * Security Role Assignment
    * Access Rights Management
    * Technical Groups Display
    * Temporary Role Activation and Blocking
    * Copy Groups from Existing User
    * Create User from Role
    * Notification Settings per Role
    * Scheduled Role Activation
""",
    'author': 'inomERP',
    'support': 'info@inomerp.in',
    'website': 'https://inomerp.in',
    'license': 'LGPL-3',
    'depends': ['base', 'mail'],
    'data': [
        'security/ir.access.csv',
        'data/scheduled_action.xml',
        'views/security_role_views.xml',
        'views/res_users_views.xml',
        'views/res_config_settings_views.xml',
        'views/menu_views.xml',
    ],
    'images': ['static/description/banner.png'],
    'application': True,
    'installable': True,
    'auto_install': False,
}
