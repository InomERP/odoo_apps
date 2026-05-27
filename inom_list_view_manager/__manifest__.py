{
    'name': 'List View Manager',
    'version': '17.0.1.0.0',
    'author': 'inomerp',
    'website': 'https://inomerp.in',
    'summary': 'Dynamic List: Hide/Show, Reorder, Rename, Search, Restore columns per user',
    'depends': ['web', 'base_setup'],
    'data': [
        'security/ir.model.access.csv',
        'views/res_config_setting_views.xml',
        'views/list_view_manager_menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'inom_list_view_manager/static/src/js/list_view_manager.js',
            'inom_list_view_manager/static/src/js/dynammic_list.js',
            'inom_list_view_manager/static/src/js/list_controller.js',
            'inom_list_view_manager/static/src/js/list_view_registry.js',
            'inom_list_view_manager/static/src/xml/dynamic_list_patch.xml',
            'inom_list_view_manager/static/src/xml/list_renderer_patch.xml',
            'inom_list_view_manager/static/src/js/list_serial_number.js',

            'inom_list_view_manager/static/src/js/copy_field_value.js',
            'inom_list_view_manager/static/src/js/list_duplicate_records.js',
            'inom_list_view_manager/static/src/xml/list_duplicate_button.xml',
            'inom_list_view_manager/static/src/js/list_column_search.js',
            'inom_list_view_manager/static/src/scss/list_manager.scss',
            'inom_list_view_manager/static/src/js/list_column_resize.js',
            'inom_list_view_manager/static/src/xml/list_serial_number.xml',
            'inom_list_view_manager/static/src/js/list_reload_button.js',
            'inom_list_view_manager/static/src/js/list_renderer_patch.js',

            # 'inom_list_view_manager/static/src/xml/list_reload_button.xml',

        ],
    },
    'images': ['static/description/banner.png'],

    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}