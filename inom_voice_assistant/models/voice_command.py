# -*- coding: utf-8 -*-
from odoo import _, api, fields, models


class VoiceCommand(models.Model):
    _name = "voice.command"
    _description = "Voice Assistant Command"
    _order = "sequence, id"

    name = fields.Char(
        required=True,
        help="Friendly label shown in the listening pill when the command runs.",
    )
    keywords = fields.Char(
        required=True,
        help="Comma-separated words/phrases to listen for, in English and/or Hindi. "
        "Example: customer, client, ग्राहक",
    )
    command_type = fields.Selection(
        [
            ("open_model", "Open / search records of a model"),
            ("open_action", "Open a specific action / screen"),
        ],
        string="Command Type",
        default="open_model",
        required=True,
    )
    model_id = fields.Many2one(
        "ir.model",
        string="Model",
        ondelete="cascade",
        help="The model to open or search (used when type is 'Open model').",
    )
    model_name = fields.Char(
        related="model_id.model",
        string="Model Name",
        store=True,
    )
    name_field = fields.Char(
        string="Match Field",
        default="name",
        help="Field used to match the spoken name. Usually 'name'.",
    )
    action_id = fields.Many2one(
        "ir.actions.act_window",
        string="Action / Screen",
        ondelete="cascade",
        help="The specific screen to open (used when type is 'Open action').",
    )
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)

    @api.model
    def get_commands(self):
        """Return active commands in a JS-friendly shape for the web client."""
        commands = self.search_read(
            [("active", "=", True)],
            ["name", "keywords", "command_type", "model_name", "action_id", "name_field"],
            order="sequence, id",
        )
        result = []
        for c in commands:
            result.append(
                {
                    "label": c["name"],
                    "keywords": [
                        k.strip().lower()
                        for k in (c["keywords"] or "").split(",")
                        if k.strip()
                    ],
                    "kind": "action" if c["command_type"] == "open_action" else "object",
                    "model": c["model_name"] or False,
                    "actionId": c["action_id"][0] if c["action_id"] else False,
                    "nameField": c["name_field"] or "name",
                }
            )
        return result

    def _menu_window_actions(self):
        """Return act_window actions reachable from the user's menus."""
        menus = self.env["ir.ui.menu"].search([("action", "!=", False)])
        actions = []
        for menu in menus:
            act = menu.action
            # menu.action is a Reference; for window menus it resolves to the
            # concrete ir.actions.act_window record.
            if act and act._name == "ir.actions.act_window":
                actions.append((menu.name, act))
        return actions

    def _notify(self, message):
        """Show a toast and reload the list."""
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Voice Commands"),
                "message": message,
                "type": "success",
                "sticky": False,
                "next": {
                    "type": "ir.actions.act_window",
                    "name": _("Voice Commands"),
                    "res_model": "voice.command",
                    "view_mode": "tree,form",
                    "views": [[False, "tree"], [False, "form"]],
                    "target": "current",
                },
            },
        }

    def action_generate_from_menus(self):
        """Create an 'open action' command for each screen in the menus.
        Saying the screen's name (e.g. 'open contacts') launches it."""
        existing = set(
            self.search([("action_id", "!=", False)]).mapped("action_id").ids
        )
        created = 0
        for menu_name, act in self._menu_window_actions():
            if act.id in existing or not menu_name:
                continue
            self.create(
                {
                    "name": menu_name,
                    "keywords": menu_name.lower(),
                    "command_type": "open_action",
                    "action_id": act.id,
                }
            )
            existing.add(act.id)
            created += 1
        return self._notify(_("%s screen command(s) added from menus.") % created)

    def action_generate_from_models(self):
        """Create an 'open model' command for each model behind the menus.
        Lets you open records by name, e.g. 'open lead Acme'."""
        existing = set(
            self.search(
                [("command_type", "=", "open_model"), ("model_name", "!=", False)]
            ).mapped("model_name")
        )
        created = 0
        for _menu_name, act in self._menu_window_actions():
            res_model = act.res_model
            if not res_model or res_model in existing:
                continue
            model_rec = self.env["ir.model"].search(
                [("model", "=", res_model)], limit=1
            )
            if not model_rec:
                continue
            label = model_rec.name or res_model
            self.create(
                {
                    "name": label,
                    "keywords": label.lower(),
                    "command_type": "open_model",
                    "model_id": model_rec.id,
                }
            )
            existing.add(res_model)
            created += 1
        return self._notify(_("%s record command(s) added from models.") % created)
