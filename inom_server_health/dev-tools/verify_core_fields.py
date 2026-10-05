#!/usr/bin/env python3
"""Check that fields this module writes to core models still exist.

Written after v19.0.5.0.0 failed to install: res.groups lost `category_id` in
Odoo 19, replaced by `privilege_id` -> res.groups.privilege. That is exactly
the kind of change a module carried forward from 17/18 will trip over, and
the error ("Invalid field 'category_id' in 'res.groups'") only surfaces at
install time.

This is a static declaration of the contract, checked against the real 19.0
sources when run with --fetch. Without network it just prints the contract.

Fields inherited via _inherits are noted, since they will not appear in the
child model's own source (e.g. ir.cron delegates name/model_id/state to
ir.actions.server).
"""
import sys

CONTRACT = {
    "res.groups": {
        "used": ["name", "comment", "sequence", "privilege_id", "implied_ids"],
        "note": "Odoo 19: category_id REMOVED -> use privilege_id "
                "(res.groups.privilege, which carries category_id).",
    },
    "res.groups.privilege": {
        "used": ["name", "description", "sequence", "category_id"],
        "note": "New in Odoo 19.",
    },
    "ir.cron": {
        "used": ["name", "model_id", "state", "code", "interval_number",
                 "interval_type", "active", "nextcall", "cron_name",
                 "failure_count"],
        "note": "name/model_id/state/code are delegated via "
                "_inherits = {'ir.actions.server': 'ir_actions_server_id'}.",
    },
    "mail.mail": {
        "used": ["subject", "body_html", "email_to", "auto_delete", "state"],
        "note": "subject/body_html delegated via "
                "_inherits = {'mail.message': 'mail_message_id'}. "
                "state values used: outgoing, exception.",
    },
    "discuss.channel": {
        "used": ["name"],
        "note": "Only message_post() is called on it.",
    },
    "mail.presence": {
        "used": ["user_id", "last_poll", "last_presence", "status"],
        "note": "Odoo 19: RENAMED from bus.presence. Table mail_presence, "
                "_log_access = False so it has no create_date/write_date. "
                "status values: online, away, offline.",
    },
    "ir.config_parameter": {
        "used": ["key", "value"],
        "note": "get_param/set_param only.",
    },
}

RAW = "https://raw.githubusercontent.com/odoo/odoo/19.0/"
SOURCES = {
    "res.groups": "odoo/addons/base/models/res_groups.py",
    "res.groups.privilege": "odoo/addons/base/models/res_groups_privilege.py",
    "ir.cron": "odoo/addons/base/models/ir_cron.py",
    "mail.mail": "addons/mail/models/mail_mail.py",
    "discuss.channel": "addons/mail/models/discuss/discuss_channel.py",
    "mail.presence": "addons/mail/models/mail_presence.py",
}
# Fields that live on a delegated parent and so will not appear in the
# child model's own source.
INHERITED = {
    "ir.cron": {"name", "model_id", "state", "code"},   # -> ir.actions.server
    "mail.mail": {"subject", "body_html"},              # -> mail.message
}


def main(fetch=False):
    if not fetch:
        for model, spec in CONTRACT.items():
            print(f"{model}: {', '.join(spec['used'])}")
            print(f"    {spec['note']}")
        print("\nRun with --fetch to check against the 19.0 sources.")
        return 0

    import re
    import urllib.request
    problems = 0
    for model, spec in CONTRACT.items():
        path = SOURCES.get(model)
        if not path:
            continue
        try:
            src = urllib.request.urlopen(RAW + path, timeout=30).read().decode()
        except Exception as exc:
            print(f"{model}: could not fetch ({exc})")
            continue
        declared = set(re.findall(r'^\s{4}(\w+)\s*=\s*fields\.', src, re.M))
        inherited = INHERITED.get(model, set())
        missing = [f for f in spec["used"]
                   if f not in declared and f not in inherited]
        if missing:
            problems += 1
            print(f"MISSING on {model}: {missing}")
        else:
            print(f"OK  {model}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main("--fetch" in sys.argv))
