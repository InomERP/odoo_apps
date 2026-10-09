import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class InomStudentFees(models.Model):
    """Raise a fee account when a student is enrolled.

    Enrolling a student created no fee account, so their Instalments block was
    empty and there was nothing to invoice or pay. Every step of the machinery
    existed — structures, schedules, invoices, payment — and nothing started
    it, so a newly enrolled student sat outside the fee system until somebody
    noticed and built one by hand.

    Matched on programme and academic year, which is how a structure is keyed.
    Quota is not held on the student, so the general structure is used; an
    institution that bills by quota sets it on the account afterwards, and the
    schedule regenerates.

    Deliberately quiet on failure. A missing or unpublished structure is a
    configuration gap, not a reason to block an enrolment — the registrar is
    admitting a student, and refusing that because finance has not published a
    fee structure would be the system getting its priorities backwards. It is
    logged, and the Fees dashboard shows students without an account.
    """
    _inherit = 'inom.student'

    def _inom_ensure_fee_account(self):
        """Create a fee account and its schedule, if one is missing.

        Batched: the existing accounts and the published structures for the
        whole recordset are read in one query each, and every missing account
        is created in a single create() call. The decisions are the same ones
        the per-student version made — same eligibility, same year, same
        structure preference (general quota first, otherwise the first match),
        same quiet skip and log line when no structure is published — only the
        number of round trips changed.
        """
        # sudo(): enrolment is done by the registrar, who has no rights on fee
        # accounts. The account is raised on the student's behalf; nothing is
        # read back to the caller beyond the records created here.
        Account = self.env['inom.fee.account'].sudo()
        # sudo(): structures are finance configuration, read only to pick the
        # template for the new account.
        Structure = self.env['inom.fee.structure'].sudo()
        created = Account.browse()

        # 1. Eligible students and the academic year each one is billed for.
        #    The institution's current year is the fallback for a student with
        #    no batch year; it is looked up once, and only if it is needed.
        candidates = []                 # [(student, year)] in recordset order
        fallback_year = None
        for student in self:
            if student.state != 'enrolled' or not student.programme_id:
                continue
            year = student.batch_id.year_id
            if not year:
                if fallback_year is None:
                    # sudo(): the institution record is configuration every
                    # role needs to read; only its current year is used.
                    fallback_year = (self.env['inom.institution'].sudo()
                                     ._inom_current().current_year_id)
                year = fallback_year
            if not year:
                continue
            candidates.append((student, year))
        if not candidates:
            return created

        student_ids = list({student.id for student, _year in candidates})
        year_ids = list({year.id for _student, year in candidates})
        programme_ids = list({student.programme_id.id for student, _year in candidates})

        # 2. Which (student, year) pairs already have an account — one query.
        existing = Account.search([('student_id', 'in', student_ids),
                                   ('year_id', 'in', year_ids)])
        taken = {(account.student_id.id, account.year_id.id) for account in existing}

        # 3. Published structures for every (programme, year) involved — one
        #    query, grouped in Python. The search order is the model order, so
        #    within a group the records keep the order a per-pair search gave.
        structures = Structure.search([
            ('programme_id', 'in', programme_ids),
            ('year_id', 'in', year_ids),
            ('state', '=', 'published'),
        ])
        no_structure = Structure.browse()      # empty recordset, no query
        structures_by_key = {}
        for structure in structures:
            key = (structure.programme_id.id, structure.year_id.id)
            structures_by_key[key] = structures_by_key.get(key, no_structure) | structure

        # 4. Decide per student, then create every missing account at once.
        vals_list = []
        for student, year in candidates:
            if (student.id, year.id) in taken:
                continue        # already has one for this year
            matches = structures_by_key.get(
                (student.programme_id.id, year.id), no_structure)
            structure = (matches.filtered(lambda s: s.quota == 'general')[:1]
                         or matches[:1])
            if not structure:
                _logger.info(
                    'INOM fees: no published structure for %s in %s, so %s has '
                    'no fee account yet',
                    student.programme_id.code, year.name, student.enrolment_no)
                continue
            # Mark the pair as taken so a student listed twice in the same
            # recordset still gets exactly one account, as before.
            taken.add((student.id, year.id))
            vals_list.append({
                'student_id': student.id,
                'year_id': year.id,
                'structure_id': structure.id,
            })
        if not vals_list:
            return created

        created = Account.create(vals_list)

        # 5. Schedules, each isolated exactly as before: a failure is logged
        #    and leaves that account without lines, it never blocks enrolment.
        for account in created:
            try:
                account._inom_action_generate_schedule()
            except Exception as err:                            # noqa: BLE001
                _logger.warning(
                    'INOM fees: fee account %s created but its schedule could '
                    'not be generated: %s', account.display_name, err)

        return created

    @api.model_create_multi
    def create(self, vals_list):
        students = super().create(vals_list)
        students._inom_ensure_fee_account()
        return students

    def write(self, vals):
        result = super().write(vals)
        # Only when the state actually moved to enrolled — a student admitted
        # then edited should not get a second account, and the search above
        # guards that anyway.
        if vals.get('state') == 'enrolled':
            self._inom_ensure_fee_account()
        return result
