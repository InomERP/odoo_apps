#!/usr/bin/env python3
"""Check that fields this module writes to core models still exist.

Written after a v19 revision failed to install: res.groups lost `category_id`
in Odoo 19, replaced by `privilege_id` -> res.groups.privilege. That is
exactly the kind of change a module carried across releases will trip over,
and the error ("Invalid field ... in 'res.groups'") only surfaces at install
time.

This copy states the contract for Odoo 17.0, checked against the real 17.0
sources when run with --fetch. Without network it just prints the contract.

Fields inherited via _inherits are noted, since they will not appear in the
child model's own source (e.g. ir.cron delegates name/model_id/state to
ir.actions.server).
"""
import sys

CONTRACT = {
    "res.groups": {
        "used": ["name", "comment", "category_id", "implied_ids"],
        "note": "Odoo 17.0: category_id -> ir.module.category directly. "
                "res.groups has no `sequence` field and "
                "res.groups.privilege does not exist before Odoo 19.",
    },
    "ir.cron": {
        "used": ["name", "model_id", "state", "code", "interval_number",
                 "interval_type", "active", "nextcall", "cron_name",
                 "numbercall", "doall"],
        "note": "name/model_id/state/code are delegated via "
                "_inherits = {'ir.actions.server': 'ir_actions_server_id'}."
                " Odoo 17 defaults numbercall to 1, so both crons set it to"
                " -1. failure_count is Odoo 18+ and is deliberately NOT in"
                " this list: tools/odoo_stats.crons() probes for the column"
                " at runtime and reports failing_count as 0 when absent.",
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
    "bus.presence": {
        "used": ["user_id", "last_poll", "last_presence", "status"],
        "note": "Odoo 17.0: table bus_presence. Renamed to mail.presence "
                "(table mail_presence) only in Odoo 19. "
                "status values: online, away, offline.",
    },
    "ir.config_parameter": {
        "used": ["key", "value"],
        "note": "get_param/set_param only.",
    },
}

RAW = "https://raw.githubusercontent.com/odoo/odoo/17.0/"
SOURCES = {
    "res.groups": "odoo/addons/base/models/res_users.py",
    "ir.cron": "odoo/addons/base/models/ir_cron.py",
    "mail.mail": "addons/mail/models/mail_mail.py",
    "discuss.channel": "addons/mail/models/discuss/discuss_channel.py",
    "bus.presence": "addons/bus/models/bus_presence.py",
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
        print("\nRun with --fetch to check against the 17.0 sources.")
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
