from odoo import models
from odoo.exceptions import UserError
from markupsafe import Markup


class MailComposeMessage(models.TransientModel):
    _inherit = 'mail.compose.message'

    def action_send_mail(self):
        for rec in self:
            body = rec.body or ""
            if body.strip() in ["", "<p><br></p>", "<p></p>", "<p><br/></p>"]:
                raise UserError("Please type a reply message before sending.")
        return super().action_send_mail()


class Base(models.AbstractModel):
    _inherit = 'base'

    def post_log_reply(self, res_id, body, parent_id):
        """
        Custom method called from JS to post log note with proper Markup body.
        Markup() tells Odoo this is safe HTML — prevents tag escaping.
        """
        record = self.browse(res_id)
        return record.message_post(
            body          = Markup(body),
            parent_id     = parent_id,
            message_type  = "comment",
            subtype_xmlid = "mail.mt_note",
        ).id