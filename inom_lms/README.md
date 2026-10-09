# University — Learning (`inom_lms`)

Part of the INOM University Management System for Odoo 20 (Community and Enterprise).

Online courses, lessons, assignments and graded submissions, served through the
INOM portal.

## What it does

- **Courses** per department, optionally linked to a subject and the teaching
  faculty member. Draft courses are invisible to students — enforced by a record
  rule, not a list filter, so a reconstructed API call gets the same answer the
  screen gives.
- **Lessons** as readings, documents (upload up to 25 MB or link), videos or
  external links. Empty lessons are refused. YouTube and Vimeo links are turned
  into their embed form; MP4/WebM/OGG play inline; PDFs are shown in the page.
- **Lesson files** are served from `/ums/lesson/<id>/file` only after the
  caller's access to that lesson is checked — never through `/web/content`.
- **Assignments** with issue and due dates, maximum marks, and live submitted /
  graded counts.
- **Submissions** flagged late automatically; graders record a mark and a line
  of feedback in one step, or return work for rework. One submission per
  student per assignment.
- **Grader guard**: marks, feedback and status can only be changed by faculty,
  HoD, dean or registrar — enforced on the model, not just in the view.

## Dependencies

`inom_portal`, `inom_student`, `inom_faculty`.

## Security

Access is granted through the suite's own role groups defined in `inom_base`
(registrar, dean, HoD, faculty, student, guardian, technical), plus record rules
in `security/inom_lms_rules.xml`.

## Running the tests

```bash
odoo-bin -d <db> -u inom_lms --test-enable --test-tags /inom_lms --stop-after-init
```

The tests build their own data, so they run on an empty database too.

## Translations

`i18n/inom_lms.pot` is the translation template. Regenerate it after changing
any user-facing string:

```bash
odoo-bin i18n export -d <db> -o inom_lms/i18n/inom_lms.pot inom_lms
```

## Licence

LGPL-3. Published by InomERP Pvt Ltd — https://inomerp.in — info@inomerp.in
