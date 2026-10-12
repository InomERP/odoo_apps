# -*- coding: utf-8 -*-
from .common import UnivFeeCommon


class TestInstallment(UnivFeeCommon):

    def _make_invoice_wrapper(self):
        return self.env["univ.fee.invoice"].create({
            "student_id": self.student.id,
            "structure_id": self.structure.id,
        })

    def test_schedule_generation(self):
        wrapper = self._make_invoice_wrapper()
        plan = self.env["univ.fee.installment.plan"].create({
            "invoice_id": wrapper.id,
            "frequency": "monthly",
            "count": 4,
            "start_date": "2030-01-01",
            "amount_total": 10000.0,
        })
        plan.generate_schedule()
        self.assertEqual(len(plan.line_ids), 4)
        self.assertAlmostEqual(sum(plan.line_ids.mapped("amount")), 10000.0, 2)

    def test_sequence_assigned(self):
        wrapper = self._make_invoice_wrapper()
        self.assertNotEqual(wrapper.name, "New")
