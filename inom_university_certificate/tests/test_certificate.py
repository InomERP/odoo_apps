# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestCertificate(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.program = cls.env["univ.program"].create({"name": "P", "code": "P"})
        cls.batch = cls.env["univ.batch"].create({"name": "B", "code": "B", "program_id": cls.program.id})
        cls.sem = cls.env["univ.semester"].create({"name": "S", "code": "S", "program_id": cls.program.id})
        cls.student = cls.env["univ.student"].create({"name": "A", "program_id": cls.program.id, "batch_id": cls.batch.id, "semester_id": cls.sem.id, "state": "active"})
        cls.tmpl = cls.env["univ.certificate.template"].create({
            "name": "Bonafide", "cert_type": "bonafide", "prefix": "BON/",
            "body_html": "<p>{student} of {program}, No {number}</p>"})

    def test_lifecycle_and_supersede(self):
        cert = self.env["univ.certificate"].create({
            "student_id": self.student.id, "template_id": self.tmpl.id})
        cert.action_approve()
        cert.action_generate()
        self.assertTrue(cert.name.startswith("BON/"))
        self.assertTrue(cert.signed_hash)
        cert.action_issue()
        self.assertEqual(cert.state, "issued")
        old_number = cert.name
        cert.action_reissue()
        self.assertEqual(cert.state, "superseded")
        self.assertTrue(cert.superseded_by_id)
        self.assertNotEqual(cert.superseded_by_id.name, old_number)
