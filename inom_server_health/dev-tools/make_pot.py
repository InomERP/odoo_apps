#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build i18n/inom_server_health.pot without a running Odoo.

`odoo-bin --i18n-export` remains authoritative -- it sees computed labels and
the strings Odoo derives from field names. This script covers what can be read
statically so the template exists and stays close to current, which is what
the review asked for.

    python3 dev-tools/make_pot.py
"""

import ast
import os
import re
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODULE = os.path.basename(ROOT)

HEADER = '''# Translation template for %(module)s.
# This file is distributed under the same licence as the module.
#
# Generated statically by dev-tools/make_pot.py. Regenerate with
# `odoo-bin --i18n-export` against a database with the module installed for
# the authoritative export.
#
msgid ""
msgstr ""
"Project-Id-Version: Odoo Server 19.0\\n"
"Report-Msgid-Bugs-To: \\n"
"Last-Translator: \\n"
"Language-Team: \\n"
"MIME-Version: 1.0\\n"
"Content-Type: text/plain; charset=UTF-8\\n"
"Content-Transfer-Encoding: \\n"
"Plural-Forms: \\n"

''' % {"module": MODULE}

FIELD_KWARGS = ("string", "help")
VIEW_ATTRS = ("string", "sum", "avg", "confirm", "placeholder", "title",
              "help", "label")
RECORD_FIELDS = ("name", "string", "comment", "description")
TEXT_TAGS = ("span", "h1", "h2", "h3", "p", "button", "label")
SKIP_DIRS = ("__pycache__", "dev-tools", "static", "i18n", "tests")


# ---------------------------------------------------------------------------
# collection
# ---------------------------------------------------------------------------

def escape(text):
    return (text.replace("\\", "\\\\").replace('"', '\\"')
                .replace("\n", "\\n").replace("\t", "\\t"))


def is_prose(text):
    """Reject tokens that are not sentences a translator should ever see."""
    if not text or len(text) > 500:
        return False
    if re.fullmatch(r"[\W\d_]+", text):
        return False
    if " " not in text and re.search(r"[=?&/{}<>#]", text):
        return False
    return not text.startswith(("?", "/", "http", "&"))


def add(entries, text, source, kind):
    text = (text or "").strip()
    if not is_prose(text):
        return
    entry = entries.setdefault(text, {"refs": [], "kind": kind})
    if source not in entry["refs"]:
        entry["refs"].append(source)


def walk_files(folder, suffix):
    for base, dirs, files in os.walk(folder):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for name in sorted(files):
            if name.endswith(suffix):
                path = os.path.join(base, name)
                yield path, os.path.relpath(path, ROOT)


# ---------------------------------------------------------------------------
# python
# ---------------------------------------------------------------------------

def is_translation_call(node):
    return (isinstance(node, ast.Call)
            and getattr(node.func, "id", None) == "_"
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str))


def is_field_call(node):
    return (isinstance(node, ast.Call)
            and getattr(getattr(node.func, "value", None), "id", None)
            == "fields")


def collect_selection(entries, list_node, ref, lineno):
    """Labels out of a [(value, label), ...] table."""
    for element in list_node.elts:
        if (isinstance(element, ast.Tuple) and len(element.elts) == 2
                and isinstance(element.elts[1], ast.Constant)
                and isinstance(element.elts[1].value, str)):
            add(entries, element.elts[1].value, "%s:%s" % (ref, lineno),
                "selection")


def collect_field_call(entries, node, ref):
    """string=, help= and any selection table on a fields.* call."""
    where = "%s:%s" % (ref, node.lineno)
    for keyword in node.keywords:
        if (keyword.arg in FIELD_KWARGS
                and isinstance(keyword.value, ast.Constant)
                and isinstance(keyword.value.value, str)):
            add(entries, keyword.value.value, where, "field")
        elif keyword.arg == "selection" and isinstance(keyword.value, ast.List):
            collect_selection(entries, keyword.value, ref, node.lineno)
    for arg in node.args:
        if isinstance(arg, ast.List):
            collect_selection(entries, arg, ref, node.lineno)


def collect_assignment(entries, node, ref):
    """_description = "..." and module-level label tables such as METRICS."""
    target = getattr(node.targets[0], "id", "")
    if target == "_description" and isinstance(node.value, ast.Constant):
        add(entries, node.value.value, "%s:%s" % (ref, node.lineno), "model")
    elif target.isupper() and isinstance(node.value, ast.List):
        collect_selection(entries, node.value, ref, node.lineno)


def scan_python_node(entries, node, ref):
    if is_translation_call(node):
        add(entries, node.args[0].value, "%s:%s" % (ref, node.lineno), "code")
    elif is_field_call(node):
        collect_field_call(entries, node, ref)
    elif isinstance(node, ast.Assign):
        collect_assignment(entries, node, ref)


def scan_python(entries):
    for path, ref in walk_files(ROOT, ".py"):
        with open(path, encoding="utf-8") as handle:
            tree = ast.parse(handle.read())
        for node in ast.walk(tree):
            scan_python_node(entries, node, ref)


# ---------------------------------------------------------------------------
# xml
# ---------------------------------------------------------------------------

def scan_xml_element(entries, element, ref):
    for attr in VIEW_ATTRS:
        if element.get(attr):
            add(entries, element.get(attr), ref, "view")
    if (element.tag == "field" and element.get("name") in RECORD_FIELDS
            and element.text and not element.get("ref")):
        add(entries, element.text, ref, "record")
    elif element.tag in TEXT_TAGS and element.text:
        add(entries, element.text, ref, "view")


def scan_xml(entries):
    for folder in ("views", "data", "security"):
        directory = os.path.join(ROOT, folder)
        if not os.path.isdir(directory):
            continue
        for path, ref in walk_files(directory, ".xml"):
            for element in ET.parse(path).getroot().iter():
                scan_xml_element(entries, element, ref)


def scan_owl_element(entries, element, ref):
    text = (element.text or "").strip()
    if text and not element.get("t-esc") and len(text.split()) <= 12:
        add(entries, text, ref, "owl")
    if element.get("title"):
        add(entries, element.get("title"), ref, "owl")


def scan_owl(entries):
    directory = os.path.join(ROOT, "static", "src", "xml")
    if not os.path.isdir(directory):
        return
    for name in sorted(os.listdir(directory)):
        if not name.endswith(".xml"):
            continue
        path = os.path.join(directory, name)
        ref = os.path.relpath(path, ROOT)
        for element in ET.parse(path).getroot().iter():
            scan_owl_element(entries, element, ref)


# ---------------------------------------------------------------------------
# output
# ---------------------------------------------------------------------------

def render(entries):
    out = [HEADER]
    for text in sorted(entries):
        meta = entries[text]
        out.append("#. module: %s (%s)\n" % (MODULE, meta["kind"]))
        for ref in meta["refs"][:6]:
            out.append("#: %s\n" % ref)
        out.append('msgid "%s"\n' % escape(text))
        out.append('msgstr ""\n\n')
    return "".join(out)


def main():
    entries = {}
    scan_python(entries)
    scan_xml(entries)
    scan_owl(entries)

    target_dir = os.path.join(ROOT, "i18n")
    os.makedirs(target_dir, exist_ok=True)
    target = os.path.join(target_dir, "%s.pot" % MODULE)
    with open(target, "w", encoding="utf-8") as handle:
        handle.write(render(entries))
    print("%s entries -> %s" % (len(entries), os.path.relpath(target, ROOT)))


if __name__ == "__main__":
    main()
