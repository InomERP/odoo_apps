# -*- coding: utf-8 -*-
"""Module installation hooks."""

import logging

_logger = logging.getLogger(__name__)


def post_init_hook(env):
    """Backfill ``edm.document.file_size`` for documents uploaded before this
    version.

    The size is copied straight from ``ir_attachment.file_size`` in a single
    set-based UPDATE, so no binary payload is ever loaded - even on a
    repository holding hundreds of thousands of documents.
    """
    env.cr.execute(
        """
        UPDATE edm_document AS d
           SET file_size = a.file_size
          FROM ir_attachment AS a
         WHERE a.res_model = 'edm.document'
           AND a.res_field = 'file'
           AND a.res_id = d.id
           AND COALESCE(d.file_size, 0) = 0
           AND COALESCE(a.file_size, 0) > 0
        """
    )
    _logger.info("inom_advance_dms: backfilled file size on %s document(s).",
                 env.cr.rowcount)

    _register_group_privilege(env)
    _grant_admin_access(env)


def _grant_admin_access(env):
    """Put the administrator into the Document Manager group.

    Odoo hides a menu item when the user cannot read the model behind its
    action, so an administrator left outside these groups sees the app with
    almost every menu missing and the dashboard failing on AccessError.

    The field that links users to groups was renamed across Odoo versions
    (``groups_id`` up to 18, ``group_ids`` in 19) and the field that
    categorises a group changed too, so both are probed at runtime instead of
    being hard-coded in XML - a wrong guess there aborts the whole install.
    """
    manager = env.ref('inom_advance_dms.group_edm_manager',
                      raise_if_not_found=False)
    if not manager:
        return

    user_fields = env['res.users']._fields
    field_name = 'group_ids' if 'group_ids' in user_fields else (
        'groups_id' if 'groups_id' in user_fields else None)
    if not field_name:
        _logger.warning(
            "inom_advance_dms: could not find the user/group relation field; "
            "assign the 'Document Manager' group manually.")
        return

    for xml_id in ('base.user_admin', 'base.user_root'):
        user = env.ref(xml_id, raise_if_not_found=False)
        if not user:
            continue
        try:
            user.sudo().write({field_name: [(4, manager.id)]})
        except Exception as error:  # never block the install over this
            _logger.warning("inom_advance_dms: could not grant %s the "
                            "Document Manager group: %s", xml_id, error)

    _logger.info("inom_advance_dms: administrator granted Document Manager.")


def _register_group_privilege(env):
    """Group the DMS groups under one heading in the user form, if supported.

    Odoo 19 replaced ``res.groups.category_id`` with ``privilege_id``. Both
    are probed, and if neither exists nothing happens - the groups remain
    assignable from Settings > Users & Companies > Groups either way.
    """
    group_fields = env['res.groups']._fields
    groups = (env.ref('inom_advance_dms.group_edm_user',
                      raise_if_not_found=False)
              or env['res.groups'].browse())
    manager = env.ref('inom_advance_dms.group_edm_manager',
                      raise_if_not_found=False)
    if manager:
        groups |= manager
    if not groups:
        return

    try:
        if 'privilege_id' in group_fields and 'res.groups.privilege' in env:
            privilege = env['res.groups.privilege'].search(
                [('name', '=', 'Advanced DMS')], limit=1)
            if not privilege:
                privilege = env['res.groups.privilege'].create(
                    {'name': 'Advanced DMS'})
            groups.write({'privilege_id': privilege.id})
        elif 'category_id' in group_fields:
            category = env['ir.module.category'].search(
                [('name', '=', 'Advanced DMS')], limit=1)
            if not category:
                category = env['ir.module.category'].create(
                    {'name': 'Advanced DMS'})
            groups.write({'category_id': category.id})
    except Exception as error:  # cosmetic only - never block the install
        _logger.warning("inom_advance_dms: could not group the security "
                        "groups in the user form: %s", error)
