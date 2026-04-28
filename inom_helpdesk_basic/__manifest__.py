{
    'name': 'Inom Helpdesk Basic',
    'version' : '19.0.0.0.0',
    'category' : 'helpdesk',
    'summary' : ' Helpdesk Basic',
    'description' : 'Basic Odoo helpdesk module manages internal tickets, '
                    'uses states, assignment, priority, validations, chatter, and workflow '
                    'for training understanding development concepts. ',
    'author' : 'InomERP',
    'website' : 'https://www.inomerp.in',
    'depends': ['web','mail','base'],
    'data': [
             'security/helpdesk_security.xml',
             'security/ir.model.access.csv',
             'data/helpdesk_sequence.xml',
             'report/helpdesk_ticket_report.xml',
             'views/helpdesk_ticket_views.xml',
             'views/helpdesk_ticket_kanban.xml',
             'views/helpdesk_ticket_search.xml',
             'views/helpdesk_menu.xml',
    ],
    'images': ['static/description/banner.png'],
    'installable' : True,
    'auto_install' : False,
    'application' : True,
}
