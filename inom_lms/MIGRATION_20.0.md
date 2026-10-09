# INOM LMS — Odoo 20 Migration

This package is the Odoo 20-compatible build of the Odoo 19 `inom_lms` module.

## Compatibility work
- Manifest version updated to `20.0.1.0.90`.
- Existing Python models, controllers, security rules, portal definitions, tests,
  translations, and static assets are preserved to keep the Odoo 19 business
  behavior unchanged.
- No Odoo 19-only deprecated decorators/field/view attributes were found during
  source inspection.
- Python files pass AST parsing and compilation checks.
- XML files pass XML parsing checks.
- Manifest data-file references were checked against the package.

## Functional scope preserved
Courses, lessons, lesson file delivery, video/PDF embedding, assignments,
submissions, grading/rework workflow, late-submission handling, portal views,
role-based access, record rules, dashboard data, and existing INOM dependencies.

## Runtime note
Final runtime confirmation requires installation in an Odoo 20 database with
the dependent INOM modules (`inom_portal`, `inom_student`, `inom_faculty`) installed.
