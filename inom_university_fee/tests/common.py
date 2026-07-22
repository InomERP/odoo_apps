# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase


class UnivFeeCommon(TransactionCase):
    """Shared setup for fee tests.

    Accounting-dependent assertions are kept light because a full chart of
    accounts is not guaranteed in every test database.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company

        cls.program = cls.env["univ.program"].create({"name": "Test Program"})
        cls.partner = cls.env["res.partner"].create({"name": "Test Student Contact"})
        cls.student = cls.env["univ.student"].create({
            "name": "Test Student",
            "partner_id": cls.partner.id,
            "program_id": cls.program.id,
            "category": "general",
            "state": "active",
        })

        cls.product = cls.env["product.product"].create({
            "name": "Tuition",
            "type": "service",
        })
        cls.head = cls.env["univ.fee.head"].create({
            "name": "Tuition",
            "code": "TUI-T",
            "product_id": cls.product.id,
        })
        cls.structure = cls.env["univ.fee.structure"].create({
            "name": "Test Structure",
            "program_id": cls.program.id,
            "category": "all",
            "line_ids": [(0, 0, {"head_id": cls.head.id, "amount": 10000.0})],
        })
