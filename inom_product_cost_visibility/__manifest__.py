{
    'name': 'INOM Product Cost Visibility',
    'version': '20.0.1.0.1',
    'category': 'Inventory',
    'summary': 'Control Product Cost Visibility',
    'description': """
INOM Product Cost Visibility
============================
Restricts visibility of the product Cost field to users belonging to the
"View Product Cost" security group.

Covered views:
    * Product Template form (Cost group)
    * Product Variant form
    * Product Variant list
    * Product Variant kanban (Cost display)
""",
    'author': 'InomERP',
    'company': 'InomERP Pvt Ltd',
    'maintainer': 'InomERP Pvt Ltd',
    'website': 'https://inomerp.in',
    'support': 'info@inomerp.in',
    'license': 'OPL-1',
    'depends': ['product', 'stock'],
    'data': [
        'security/product_cost_groups.xml',
        'views/product_views.xml',
    ],
    'images': ['static/description/banner.png'],
    'installable': True,
    'application': False,
    'auto_install': False,
}
