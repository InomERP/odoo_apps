

from odoo import models, fields, api
import json

class InomListViewManager(models.Model):
    _name = 'inom.list.view.manager'
    _description = 'Inom List View Manager - User Column Preferences'
    _rec_name = 'inom_model_name'

    inom_user_id = fields.Many2one(
        'res.users',
        string='User',
        default=lambda self: self.env.user,
        required=True,
        ondelete='cascade',
        index=True
    )

    # Which Odoo model this config applies to (e.g. 'sale.order')
    inom_model_name = fields.Char(
        string='Model Name',
        required=True,
        index=True
    )

    # Which list view (ir.ui.view id) this config applies to
    inom_view_id = fields.Integer(
        string='View ID',
        required=True,
        index=True
    )

    # JSON string storing column config:
    # { "columns": [{ "name": "partner_id", "label": "Customer", "hidden": false, "order": 0 }] }
    inom_column_config = fields.Text(
        string='Column Config (JSON)'
    )

    # Prevent duplicate configs for same user+model+view
    _sql_constraints = [
        (
            'unique_user_model_view',
            'UNIQUE(inom_user_id, inom_model_name, inom_view_id)',
            'Only one config per user per view is allowed.'
        )
    ]

    # ─────────────────────────────────────────────────────────────
    # PYTHON METHODS — called from JavaScript via RPC
    # ─────────────────────────────────────────────────────────────

    @api.model
    def inom_get_column_config(self, model_name, view_id):
        """
        JS calls this to LOAD the saved column config.
        Returns JSON string or '{}' if no config saved yet.
        """
        record = self.search([
            ('inom_user_id', '=', self.env.uid),
            ('inom_model_name', '=', model_name),
            ('inom_view_id', '=', view_id),
        ], limit=1)
        return record.inom_column_config if record else '{}'

    @api.model
    def inom_save_column_config(self, model_name, view_id, config_json):
        """
        JS calls this to SAVE the column config.
        Creates a new record or updates the existing one.
        """
        record = self.search([
            ('inom_user_id', '=', self.env.uid),
            ('inom_model_name', '=', model_name),
            ('inom_view_id', '=', view_id),
        ], limit=1)

        if record:
            record.inom_column_config = config_json
        else:
            self.create({
                'inom_user_id': self.env.uid,
                'inom_model_name': model_name,
                'inom_view_id': view_id,
                'inom_column_config': config_json,
            })
        return True

    @api.model
    def inom_reset_column_config(self, model_name, view_id):
        """
        JS calls this to RESET (delete) the saved config.
        View will return to Odoo's default column layout.
        """
        self.search([
            ('inom_user_id', '=', self.env.uid),
            ('inom_model_name', '=', model_name),
            ('inom_view_id', '=', view_id),
        ]).unlink()
        return True

    @api.model
    def get_serial_number_setting(self):
            value = self.env["ir.config_parameter"].sudo().get_param(
                "inom_lvm.enable_serial_number",
                default=False
            )
            print("PARAM VALUE gsrfvbdshtrdxgfbfhgtrfghgthrdgttrerd=", value)

            return value in ["True", True, "1"]

    @api.model
    def get_toggle_color(self):

        return self.env["ir.config_parameter"].sudo().get_param(
            "inom_lvm.toggle_color",
            "#875A7B"
        )

    @api.model
    def get_header_color(self):

        return self.env["ir.config_parameter"].sudo().get_param(
            "inom_lvm.header_color",
            "#875A7B"
        )

    @api.model
    def get_header_text_color(self):

        return self.env["ir.config_parameter"].sudo().get_param(
            "inom_lvm.header_text_color",
            "#FFFFFF"
        )