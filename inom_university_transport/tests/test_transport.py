# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestTransport(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.program = cls.env["univ.program"].create({"name": "P", "code": "P"})
        cls.batch = cls.env["univ.batch"].create({"name": "B", "code": "B", "program_id": cls.program.id})
        cls.sem = cls.env["univ.semester"].create({"name": "S", "code": "S", "program_id": cls.program.id})
        cls.student = cls.env["univ.student"].create({"name": "A", "program_id": cls.program.id, "batch_id": cls.batch.id, "semester_id": cls.sem.id, "state": "active"})
        cls.vehicle = cls.env["univ.transport.vehicle"].create({"regno": "X1", "capacity": 2})
        cls.route = cls.env["univ.transport.route"].create({"name": "R", "vehicle_id": cls.vehicle.id, "fee_amount": 0.0})
        cls.stop = cls.env["univ.transport.stop"].create({"name": "S1", "route_id": cls.route.id})

    def test_subscription_flow(self):
        sub = self.env["univ.transport.subscription"].create({
            "student_id": self.student.id, "route_id": self.route.id, "stop_id": self.stop.id})
        sub.action_map_stop()
        self.assertEqual(sub.state, "mapped")
        sub.action_add_fee()
        self.assertEqual(sub.state, "fee_added")
        sub.action_issue_pass()
        self.assertEqual(sub.state, "issued")
        self.assertEqual(self.route.seats_used, 1)
