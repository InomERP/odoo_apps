from odoo.exceptions import UserError
from odoo.tests import HttpCase, TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestPostLogReply(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create({"name": "Reply Partner"})
        cls.parent = cls.partner.message_post(
            body="Original note", message_type="comment", subtype_xmlid="mail.mt_note",
        )

    def test_post_log_reply(self):
        message_id = self.partner.post_log_reply("<p>quoted</p><p>my reply</p>", parent_id=self.parent.id)
        message = self.env["mail.message"].browse(message_id)
        self.assertEqual(message.model, "res.partner")
        self.assertEqual(message.res_id, self.partner.id)
        self.assertEqual(message.parent_id, self.parent)
        self.assertEqual(message.message_type, "comment")
        self.assertEqual(message.subtype_id, self.env.ref("mail.mt_note"))
        self.assertIn("<p>my reply</p>", message.body)

    def test_post_log_reply_sanitized(self):
        message_id = self.partner.post_log_reply("<p>hi</p><script>alert(1)</script>")
        body = self.env["mail.message"].browse(message_id).body
        self.assertNotIn("<script", body)
        self.assertIn("<p>hi</p>", body)

    def test_post_log_reply_empty(self):
        for body in ("", "<p><br></p>", "<p></p>", False):
            with self.assertRaises(UserError):
                self.partner.post_log_reply(body)

    def test_post_log_reply_foreign_parent(self):
        other = self.env["res.partner"].create({"name": "Other"})
        message_id = other.post_log_reply("<p>x</p>", parent_id=self.parent.id)
        self.assertFalse(self.env["mail.message"].browse(message_id).parent_id)

    def test_post_log_reply_missing_parent(self):
        message_id = self.partner.post_log_reply("<p>x</p>", parent_id=999999999)
        self.assertFalse(self.env["mail.message"].browse(message_id).parent_id)

    def test_post_log_reply_multi_records(self):
        partners = self.partner | self.env["res.partner"].create({"name": "Second"})
        with self.assertRaises(ValueError):
            partners.post_log_reply("<p>x</p>")

    def test_post_log_reply_model_without_chatter(self):
        currency = self.env.ref("base.USD")
        with self.assertRaises(UserError):
            currency.post_log_reply("<p>x</p>")


@tagged("post_install", "-at_install")
class TestComposerEmptyCheck(TransactionCase):

    def _composer(self, body, **ctx):
        partner = self.env["res.partner"].create({"name": "Composer Partner", "email": "c@example.com"})
        return self.env["mail.compose.message"].with_context(
            default_model="res.partner",
            default_res_ids=[partner.id],
            default_composition_mode="comment",
            **ctx,
        ).create({"body": body})

    def test_empty_body_blocked_for_reply(self):
        composer = self._composer("<p><br></p>", inom_chatter_reply=True)
        with self.assertRaises(UserError):
            composer.action_send_mail()

    def test_empty_body_allowed_outside_reply(self):
        # Standard composers (templates, attachment-only mails...) must not be affected
        composer = self._composer("<p><br></p>")
        composer.action_send_mail()

    def test_reply_with_body_sent(self):
        composer = self._composer("<p>Hello</p>", inom_chatter_reply=True)
        composer.action_send_mail()


@tagged("post_install", "-at_install")
class TestChatterReplyTour(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.customer = cls.env["res.partner"].create({
            "name": "Reply Customer",
            "email": "reply.customer@example.com",
        })
        cls.record = cls.env["res.partner"].create({"name": "Reply Record"})
        cls.note = cls.record.message_post(
            body="Original internal note",
            message_type="comment",
            subtype_xmlid="mail.mt_note",
            author_id=cls.env.ref("base.partner_root").id,
        )
        cls.comment = cls.record.message_post(
            body="Original customer message",
            message_type="comment",
            subtype_xmlid="mail.mt_comment",
            author_id=cls.customer.id,
        )
        cls.url = f"/odoo/res.partner/{cls.record.id}"

    def _record_messages(self, subtype_xmlid):
        return self.env["mail.message"].search([
            ("model", "=", "res.partner"),
            ("res_id", "=", self.record.id),
            ("subtype_id", "=", self.env.ref(subtype_xmlid).id),
        ])

    def test_reply_to_log_note(self):
        before = self._record_messages("mail.mt_note")
        self.start_tour(self.url, "inom_chatter_reply_log_note_tour", login="admin")
        reply = self._record_messages("mail.mt_note") - before
        self.assertEqual(len(reply), 1)
        self.assertEqual(reply.parent_id, self.note)
        self.assertEqual(reply.author_id, self.env.ref("base.user_admin").partner_id)
        self.assertIn("Original internal note", reply.body)
        # user text is escaped, not interpreted as HTML
        self.assertIn("Reply &lt;b&gt;not bold&lt;/b&gt;", reply.body)
        self.assertNotIn("<b>not bold</b>", reply.body)

    def test_reply_to_log_note_discard(self):
        before = self._record_messages("mail.mt_note")
        self.start_tour(self.url, "inom_chatter_reply_log_note_discard_tour", login="admin")
        self.assertEqual(self._record_messages("mail.mt_note"), before)

    def test_reply_to_comment(self):
        before = self._record_messages("mail.mt_comment")
        self.start_tour(self.url, "inom_chatter_reply_comment_tour", login="admin")
        reply = self._record_messages("mail.mt_comment") - before
        self.assertEqual(len(reply), 1)
        self.assertEqual(reply.parent_id, self.comment)
        self.assertEqual(reply.message_type, "comment")
        self.assertIn(self.customer, reply.partner_ids)
        self.assertEqual(reply.subject, "Reply Message")
        self.assertIn("Original customer message", reply.body)


    def test_channel_reply_stays_native(self):
        channel = self.env["discuss.channel"].create({"name": "Reply Channel"})
        channel._add_members(users=self.env.ref("base.user_admin"))
        channel.message_post(
            body="Hello channel",
            message_type="comment",
            subtype_xmlid="mail.mt_comment",
            author_id=self.customer.id,
        )
        self.start_tour(
            f"/odoo/discuss?active_id=discuss.channel_{channel.id}",
            "inom_chatter_reply_channel_native_tour",
            login="admin",
        )
