#!/usr/bin/env python3
"""Validate every view arch against Odoo 19's own RNG schemas.

Written after v19.0.4.0.0 shipped a search view using <group expand="0"
string="Group By">. Odoo 19's search_view.rng allows <group> neither `expand`
nor `string`, and requires its children to be <field> -- so the module failed
to upgrade with a bare "Invalid view definition" and no useful detail.

Guessing at Odoo's view rules produces near-misses. Reading the schema does
not. The schemas live in this directory, copied from
odoo/addons/base/rng/ on the 19.0 branch.

Usage:  python3 dev-tools/verify_views.py [module_dir]
"""
import glob
import os
import sys

try:
    from lxml import etree
except ImportError:
    sys.exit("lxml required: pip install lxml")

HERE = os.path.dirname(os.path.abspath(__file__))
SCHEMAS = {}
for kind in ("search", "list", "graph"):
    path = os.path.join(HERE, f"{kind}_view.rng")
    if os.path.exists(path):
        SCHEMAS[kind] = etree.RelaxNG(etree.parse(path))


def main(root):
    failures = 0
    checked = 0
    for path in glob.glob(os.path.join(root, "**", "*.xml"), recursive=True):
        if "dev-tools" in path:
            continue
        try:
            tree = etree.parse(path)
        except etree.XMLSyntaxError as exc:
            print(f"MALFORMED {path}: {exc}")
            failures += 1
            continue
        for arch in tree.xpath('//field[@name="arch"]'):
            for node in arch:
                schema = SCHEMAS.get(node.tag)
                if schema is None:
                    continue
                checked += 1
                doc = etree.ElementTree(
                    etree.fromstring(etree.tostring(node)))
                if not schema.validate(doc):
                    failures += 1
                    name = arch.getparent().xpath(
                        'field[@name="name"]/text()') or [path]
                    print(f"INVALID <{node.tag}> in {name[0]}")
                    for err in schema.error_log:
                        print(f"    {err.message}")
    print(f"{checked} view(s) checked — "
          + ("all valid" if not failures else f"{failures} INVALID"))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1
                  else os.path.dirname(HERE)))
