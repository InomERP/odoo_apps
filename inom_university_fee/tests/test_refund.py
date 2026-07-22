# -*- coding: utf-8 -*-
from .common import UnivFeeCommon


class TestRefund(UnivFeeCommon):

    def setUp(self):
        super().setUp()
        self.company.fee_refund_threshold = 25000.0
        self.wrapper = self.env["univ.fee.invoice"].create({
            "student_id": self.student.id,
            "structure_id": self.structure.id,
        })

    def test_small_refund_single_approval(self):
        req = self.env["univ.fee.refund.request"].create({
            "invoice_id": self.wrapper.id,
            "amount": 1000.0,
            "reason": "Test",
        })
        self.assertFalse(req.needs_second_level)
        req.action_submit()
        req.action_approve()
        self.assertEqual(req.state, "approved")

    def test_large_refund_needs_second_level(self):
        rec = self.env["univ.fee.refund.request"].new({
            "invoice_id": self.wrapper.id,
            "amount": 30000.0,
        })
        rec._compute_needs_second_level()
        self.assertTrue(rec.needs_second_level)
