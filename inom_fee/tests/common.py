"""Shared fixtures for the inom_fee tests.

Every test builds its own institution, programme, year and structure, so the
suite runs on an empty database as well as on one seeded with demo data.
"""
from datetime import date

from odoo.tests import TransactionCase


class InomFeeCommon(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        env = cls.env
        cls.institution = env['inom.institution'].create({
            'name': 'Fee Test University',
            'short_name': 'FTU',
            'code': 'FTU-TEST',
        })
        cls.department = env['inom.department'].create({
            'name': 'Fee Test Department',
            'code': 'FTDEP',
            'institution_id': cls.institution.id,
        })
        cls.programme = env['inom.programme'].create({
            'name': 'Fee Test Programme',
            'code': 'FTPROG',
            'department_id': cls.department.id,
        })
        cls.year = env['inom.academic.year'].create({
            'name': 'FT-2090-91',
            'date_start': date(2090, 7, 1),
            'date_end': date(2091, 6, 30),
        })
        cls.batch = env['inom.batch'].create({
            'programme_id': cls.programme.id,
            'year_id': cls.year.id,
            'section': 'A',
        })

    @classmethod
    def _make_structure(cls, code='FT-GEN', quota='general', publish=True,
                        components=(('Tuition', 60000.0), ('Library', 40000.0)),
                        instalments=(('First', 40.0, 0), ('Second', 60.0, 120))):
        structure = cls.env['inom.fee.structure'].create({
            'name': f'Structure {code}',
            'code': code,
            'programme_id': cls.programme.id,
            'year_id': cls.year.id,
            'quota': quota,
            'component_ids': [(0, 0, {'name': name, 'amount': amount})
                              for name, amount in components],
            'instalment_ids': [(0, 0, {'name': name, 'percentage': pct,
                                       'due_offset_days': days, 'sequence': seq})
                               for seq, (name, pct, days) in enumerate(instalments)],
        })
        if publish:
            structure._inom_action_publish()
        return structure

    @classmethod
    def _make_student(cls, name='Fee Test Student', **extra):
        vals = {
            'name': name,
            'programme_id': cls.programme.id,
            'batch_id': cls.batch.id,
            'state': 'enrolled',
        }
        vals.update(extra)
        return cls.env['inom.student'].create(vals)
