# -*- coding: utf-8 -*-
from odoo.exceptions import UserError
from odoo.tests.common import tagged

from .common import AdmissionCommon


@tagged("post_install", "-at_install")
class TestSeatQuota(AdmissionCommon):
    def _make_seat(self, capacity):
        return self.env["univ.quota.seat"].create(
            {
                "program_id": self.program.id,
                "quota_id": self.quota.id,
                "round_id": self.admission_round.id,
                "capacity": capacity,
            }
        )

    def test_available_seats_initial(self):
        seat = self._make_seat(10)
        self.assertEqual(seat.available_seats, 10)
        self.assertEqual(seat.used_seats, 0)

    def test_reserved_reduces_availability(self):
        seat = self._make_seat(2)
        applicant = self._make_applicant()
        applicant.action_issue_offer()
        seat.invalidate_recordset()
        self.assertEqual(seat.reserved_seats, 1)
        self.assertEqual(seat.available_seats, 1)

    def test_seat_full_blocks_offer(self):
        self._make_seat(1)
        first = self._make_applicant()
        first.action_issue_offer()
        second = self._make_applicant(email="second@example.com")
        with self.assertRaises(UserError):
            second.action_issue_offer()
