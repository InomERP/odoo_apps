# -*- coding: utf-8 -*-
{
    "name": "Inom Voice Assistant",

    "version": "18.0.1.0.0",

    "category": "Productivity",

    "summary": "Control Odoo using smart voice commands with multilingual support.",

    "description": """
Inom Voice Assistant
====================

Inom Voice Assistant enhances the Odoo experience by allowing users to interact
with the system through voice commands. Users can perform actions such as
opening records, searching data, navigating screens, and creating new entries
without manual interaction.

Key Features
------------
- Smart voice-based navigation across Odoo modules
- Open, search, and create records using voice commands
- Microphone access through top bar integration
- Keyboard shortcut support (Ctrl + Space)
- English and Hindi voice recognition support
- Dynamic command configuration from backend
- Automatic command generation support
- Fast and user-friendly interaction workflow
- Easy customization and extensibility
- Seamless integration with Odoo backend

This module improves productivity and provides a modern hands-free experience
for users working with Odoo applications.
""",

    "author": "InomERP",

    "website": "https://inomerp.in",

    "license": "LGPL-3",

    "depends": [
        "web",
        "base",
    ],

    "data": [
        "security/ir.model.access.csv",
        "views/voice_command_views.xml",
        "data/voice_command_data.xml",
    ],

    "assets": {
        "web.assets_backend": [
            "inom_voice_assistant/static/src/scss/inom_voice_assistant.scss",
            "inom_voice_assistant/static/src/js/command_config.js",
            "inom_voice_assistant/static/src/js/command_parser.js",
            "inom_voice_assistant/static/src/js/inom_voice_assistant_service.js",
            "inom_voice_assistant/static/src/js/inom_voice_assistant_systray.js",
            "inom_voice_assistant/static/src/js/inom_voice_assistant_overlay.js",
            "inom_voice_assistant/static/src/xml/inom_voice_assistant_systray.xml",
            "inom_voice_assistant/static/src/xml/inom_voice_assistant_overlay.xml",
        ],
    },

    "installable": True,

    "application": True,
}


