from odoo import _, models
from odoo.exceptions import UserError
from odoo.tools import is_html_empty
from markupsafe import Markup


class MailComposeMessage(models.TransientModel):
    _inherit = 'mail.compose.message'

    def action_send_mail(self):
        # Only enforce for composers opened by our Reply action, so other
        # flows (templates, attachment-only mails, mass mailing) are untouched.
        if self.env.context.get('inom_chatter_reply'):
            for rec in self:
                if is_html_empty(rec.body):
                    raise UserError(_("Please type a reply message before sending."))
        return super().action_send_mail()


class Base(models.AbstractModel):
    _inherit = 'base'

    def post_log_reply(self, body, parent_id=False):
        """
        Custom method called from JS to post a log note reply with proper Markup body.
        Markup() tells Odoo this is safe HTML — prevents tag escaping; the body is
        still sanitized by mail.message's Html field on write.
        """
        self.ensure_one()
        if not hasattr(self, 'message_post'):
            raise UserError(_("This document does not support chatter messages."))
        if is_html_empty(body):
            raise UserError(_("Please type a reply message before sending."))
        if parent_id:
            parent = self.env['mail.message'].browse(parent_id).exists()
            if not parent or parent.model != self._name or parent.res_id != self.id:
                parent_id = False
        return self.message_post(
            body=Markup(body),
            parent_id=parent_id,
            message_type="comment",
            subtype_xmlid="mail.mt_note",
        ).id
