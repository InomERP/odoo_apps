from odoo import api, fields, models
from odoo.exceptions import ValidationError
import ast
import re

EMAIL_REGEX = r"[^@]+@[^@]+\.[^@]+"

ICP_CC_ENABLE = "inom_mail_cc_bcc.email_cc_enable"
ICP_BCC_ENABLE = "inom_mail_cc_bcc.email_bcc_enable"
ICP_REPLY_ENABLE = "inom_mail_cc_bcc.reply_to_enable"
ICP_CC_TEXT = "inom_mail_cc_bcc.email_cc_text"
ICP_BCC_TEXT = "inom_mail_cc_bcc.email_bcc_text"
ICP_REPLY_TEXT = "inom_mail_cc_bcc.reply_to_text"


class MailComposeMessage(models.TransientModel):
    _inherit = "mail.compose.message"

    email_cc = fields.Char(string="CC")
    email_bcc = fields.Char(string="BCC")
    show_bcc = fields.Boolean(string="Add BCC")

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        icp = self.env["ir.config_parameter"].sudo()

        if icp.get_bool(ICP_CC_ENABLE, False):
            res["email_cc"] = icp.get_str(ICP_CC_TEXT, "")
        if icp.get_bool(ICP_BCC_ENABLE, False):
            res["email_bcc"] = icp.get_str(ICP_BCC_TEXT, "")
            res["show_bcc"] = True

        return res

    @staticmethod
    def _validate_emails(emails):
        if not emails:
            return
        for email in emails.split(","):
            email = email.strip()
            if email and not re.fullmatch(EMAIL_REGEX, email):
                raise ValidationError("Invalid email: %s" % email)

    @staticmethod
    def _parse_headers(headers):
        """Return Odoo mail headers as a normal dict.

        ``mail.mail.headers`` is a Text field in Odoo 20 and is normally
        stored as the string representation of a Python dict.  Calling
        ``dict(headers)`` on that string raises ``ValueError``.
        """
        if not headers:
            return {}
        if isinstance(headers, dict):
            return dict(headers)
        try:
            parsed = ast.literal_eval(headers)
        except (ValueError, SyntaxError, TypeError):
            return {}
        return dict(parsed) if isinstance(parsed, dict) else {}

    def _prepare_mail_values(self, res_ids):
        """Prepare mail values for Odoo 20.

        In comment mode Odoo passes these values to ``message_post``;
        ``email_cc``/``email_bcc`` are not accepted there.  We therefore
        only inject them for mass-mail mode.  Comment-mode delivery is
        handled after the message is created in ``_action_send_mail_comment``.
        """
        mail_values = super()._prepare_mail_values(res_ids)
        icp = self.env["ir.config_parameter"].sudo()
        reply_to = icp.get_str(ICP_REPLY_TEXT, "") if icp.get_bool(ICP_REPLY_ENABLE, False) else ""

        for res_id, values in mail_values.items():
            if self.composition_mode == "mass_mail":
                if self.email_cc:
                    values["email_cc"] = self.email_cc
                if self.email_bcc:
                    headers = self._parse_headers(values.get("headers"))
                    headers["Bcc"] = self.email_bcc
                    values["headers"] = repr(headers)
                if reply_to:
                    values["reply_to"] = reply_to
            mail_values[res_id] = values
        return mail_values

    def _apply_comment_mail_headers(self, messages):
        """Apply CC/BCC/Reply-To to the mail.mail rows created by message_post."""
        if not messages:
            return
        icp = self.env["ir.config_parameter"].sudo()
        reply_to = icp.get_str(ICP_REPLY_TEXT, "") if icp.get_bool(ICP_REPLY_ENABLE, False) else ""
        mails = self.env["mail.mail"].search([("mail_message_id", "in", messages.ids)])
        for mail in mails:
            if self.email_cc:
                mail.email_cc = self.email_cc
            if reply_to:
                mail.reply_to = reply_to
            if self.email_bcc:
                # Odoo 20 mail.mail has no email_bcc field. Store Bcc as an
                # RFC header; the mail server uses it for SMTP recipients.
                headers = self._parse_headers(mail.headers)
                headers["Bcc"] = self.email_bcc
                mail.headers = repr(headers)

    def _action_send_mail_comment(self, res_ids):
        """Use Odoo's comment flow, then apply custom CC/BCC/Reply-To."""
        messages = super()._action_send_mail_comment(res_ids)
        self._apply_comment_mail_headers(messages)
        return messages

    def action_send_mail(self):
        for wizard in self:
            wizard._validate_emails(wizard.email_cc)
            wizard._validate_emails(wizard.email_bcc)
        return super().action_send_mail()
