# -*- coding: utf-8 -*-
from . import models
from . import controllers
from . import wizard


def _post_install_hook(env):
    """Create the "Wallet" front-end menu for every published website.

    Done in Python instead of XML so we don't depend on a specific
    parent-menu xml id (which has changed between Odoo versions and
    differs in multi-website setups).
    """
    Menu = env['website.menu'].sudo()
    for website in env['website'].sudo().search([]):
        # Skip if a wallet menu already exists for this website.
        existing = Menu.search([
            ('website_id', '=', website.id),
            ('url', '=', '/shop/wallet'),
        ], limit=1)
        if existing:
            continue
        # Find the website's main (root) menu. The root menu has
        # parent_id = False on the same website.
        main_menu = Menu.search([
            ('website_id', '=', website.id),
            ('parent_id', '=', False),
        ], limit=1)
        if not main_menu:
            # Fallback: take the menu with the lowest sequence on this site.
            main_menu = Menu.search(
                [('website_id', '=', website.id)],
                order='sequence,id',
                limit=1,
            )
        if not main_menu:
            continue
        Menu.create({
            'name': 'Wallet',
            'url': '/shop/wallet',
            'parent_id': main_menu.id,
            'website_id': website.id,
            'sequence': 60,
        })


def _uninstall_hook(env):
    """Remove the wallet website menu when the module is uninstalled."""
    env['website.menu'].sudo().search([
        ('url', '=', '/shop/wallet'),
    ]).unlink()
