# -*- coding: utf-8 -*-
from .common import UnivFeeCommon


class TestFeeStructure(UnivFeeCommon):

    def test_structure_total(self):
        self.assertEqual(self.structure.amount_total, 10000.0)

    def test_structure_confirm(self):
        self.structure.action_confirm()
        self.assertEqual(self.structure.state, "confirmed")

    def test_student_domain(self):
        self.structure.action_confirm()
        wizard = self.env["univ.fee.bulk.invoice.wizard"].create({
            "structure_id": self.structure.id,
            "due_date": "2030-01-01",
        })
        self.assertIn(self.student, self.env["univ.student"].search(
            wizard._student_domain()))
