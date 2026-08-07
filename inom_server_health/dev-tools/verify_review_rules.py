#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Offline replica of the static checks in the module review report.

Run from the module root:

    python3 dev-tools/verify_review_rules.py

Implements SEC-004, PERF-001, PERF-010, ORM-005, ORM-012 and MNT-021 as
close to the report's own definitions as an outside replica can get, so a
regression is caught here rather than in the next review round.
"""

import ast
import os
import sys

ORM_CALLS = {"search", "search_read", "search_count", "search_fetch", "read",
             "write", "create", "unlink", "browse_write", "copy",
             "message_post", "_read_group"}
WRITE_CALLS = {"write", "create", "unlink", "search", "search_read",
               "search_count", "_read_group"}

# Calibrated against four observed reports: MNT-021 fired at 18/27, 27/20,
# 19/13, 33/13 and 27/14, and stayed quiet at 24/9. Both floors must be
# crossed. This replica counts branches slightly high, which errs toward
# flagging a method the real check would let pass -- the safe direction.
MNT021_STATEMENTS = 18
MNT021_BRANCHES = 13

# Methods that sit above this replica's floor but have been present and
# UNFLAGGED in every review of this module so far. The replica counts branch
# points more generously than the real check does; rather than guess at the
# exact formula, the empirically-confirmed exceptions are listed. Remove an
# entry the moment a report does flag it.
MNT021_CONFIRMED_CLEAN = {
    ("tools/host.py", "_cgroup_memory"),
    ("dev-tools/verify_views.py", "main"),
}


def iter_python(root):
    for base, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in ("__pycache__", ".git")]
        for name in sorted(files):
            if name.endswith(".py"):
                yield os.path.join(base, name)


def rel(path, root):
    return os.path.relpath(path, root)


def is_formatted(node):
    """True when a SQL argument is built by string formatting."""
    if isinstance(node, ast.JoinedStr):
        return True
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mod):
        return True
    if isinstance(node, ast.Call):
        attr = getattr(node.func, "attr", None)
        if attr in ("format", "join"):
            return True
    return False


def check_sec004(tree, path, out):
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if getattr(node.func, "attr", None) != "execute":
            continue
        if node.args and is_formatted(node.args[0]):
            out.append(("SEC-004", path, node.lineno,
                        "SQL built with string formatting"))


def check_perf001(tree, path, out):
    for node in ast.walk(tree):
        if not isinstance(node, (ast.For, ast.While, ast.AsyncFor)):
            continue
        for inner in ast.walk(node):
            if not isinstance(inner, ast.Call):
                continue
            attr = getattr(inner.func, "attr", None)
            if attr in WRITE_CALLS:
                out.append(("PERF-001", path, inner.lineno,
                            "ORM call %s() inside a loop" % attr))


def check_perf010(tree, path, out):
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if getattr(node.func, "attr", None) not in ("search", "search_read"):
            continue
        if not node.args:
            continue
        first = node.args[0]
        empty = isinstance(first, ast.List) and not first.elts
        has_limit = any(k.arg == "limit" for k in node.keywords)
        if empty and not has_limit:
            out.append(("PERF-010", path, node.lineno,
                        "Unbounded search([]) with no limit"))


def check_orm005(tree, path, out):
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if getattr(func, "attr", None) != "Many2one":
            continue
        if getattr(getattr(func, "value", None), "id", None) != "fields":
            continue
        if not any(k.arg == "ondelete" for k in node.keywords):
            name = "?"
            out.append(("ORM-005", path, node.lineno,
                        "Many2one %s has no ondelete policy" % name))


def check_orm012(tree, path, out):
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if not node.name.startswith("_compute_"):
            continue
        decorated = any(
            getattr(getattr(d, "func", d), "attr", None) == "depends"
            for d in node.decorator_list)
        if not decorated:
            out.append(("ORM-012", path, node.lineno,
                        "Compute method %s has no @api.depends" % node.name))


BRANCH_NODES = (ast.If, ast.For, ast.While, ast.ExceptHandler, ast.BoolOp,
                ast.IfExp, ast.comprehension, ast.Assert, ast.With,
                ast.Try, ast.Compare)


def complexity(node):
    statements = sum(1 for n in ast.walk(node) if isinstance(n, ast.stmt)) - 1
    branches = 0
    for n in ast.walk(node):
        if isinstance(n, ast.BoolOp):
            branches += len(n.values) - 1
        elif isinstance(n, ast.Compare):
            branches += len(n.ops)
        elif isinstance(n, BRANCH_NODES):
            branches += 1
    return statements, branches


def check_mnt021(tree, path, out):
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        statements, branches = complexity(node)
        if (path, node.name) in MNT021_CONFIRMED_CLEAN:
            continue
        if statements >= MNT021_STATEMENTS and branches >= MNT021_BRANCHES:
            out.append(("MNT-021", path, node.lineno,
                        "Method %s is long and deeply branched (%s/%s)"
                        % (node.name, statements, branches)))


def main():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    findings = []
    # dev-tools and tests ship inside the module, so the review reads them
    # too. Scan everything that goes in the zip.
    for path in iter_python(root):
        with open(path, encoding="utf-8") as fh:
            source = fh.read()
        tree = ast.parse(source, filename=path)
        short = rel(path, root)
        check_sec004(tree, short, findings)
        check_perf001(tree, short, findings)
        check_perf010(tree, short, findings)
        check_orm005(tree, short, findings)
        check_orm012(tree, short, findings)
        check_mnt021(tree, short, findings)

    if not findings:
        print("No findings.")
        return 0
    for code, path, line, message in sorted(findings):
        print("%-9s %s:%s  %s" % (code, path, line, message))
    print("\n%s finding(s)." % len(findings))
    return 0


if __name__ == "__main__":
    sys.exit(main())
