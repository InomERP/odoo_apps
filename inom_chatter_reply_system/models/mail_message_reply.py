from odoo import models, fields, api

class MailMessageReply(models.Model):
    _name = 'mail.message.reply'
    _description = 'Chatter Message Reply'
    _order = 'create_date asc'

    parent_message_id = fields.Many2one('mail.message',string='Parent Message',required=True,
        ondelete='cascade'       # parent delete ho to reply bhi delete
    )

    body = fields.Html(
        string='Reply',
        required=True,
        sanitize=True
    )

    # ── Type: message ya log note ────────────────────────
    reply_type = fields.Selection(
        [
            ('comment', 'Message'),   # SEND button
            ('note',    'Log Note'),  # LOG button
        ],
        string='Reply Type',
        required=True,
        default='comment'
    )

    # ── Author ───────────────────────────────────────────
    author_id = fields.Many2one(
        'res.partner',
        string='Author',
        default=lambda self: self.env.user.partner_id
    )

    # ── Related Record (konse model ka record hai) ───────
    res_id = fields.Integer(
        string='Record ID'
    )
    res_model = fields.Char(
        string='Record Model'
    )

    # ── Timestamps (auto) ────────────────────────────────
    create_date = fields.Datetime(string='Replied On', readonly=True)
    create_uid  = fields.Many2one('res.users', string='Replied By', readonly=True)


    # ════════════════════════════════════════════════════
    #  METHODS
    # ════════════════════════════════════════════════════

    def action_send_reply(self, parent_message_id, body, reply_type='comment'):
        """
        JS se call hoga jab user SEND ya LOG button click kare.
        Ek reply record banata hai aur mail.message me bhi post karta hai.
        """
        parent_msg = self.env['mail.message'].browse(parent_message_id)

        # 1. Reply record save karo apne model me
        reply = self.create({
            'parent_message_id': parent_message_id,
            'body':              body,
            'reply_type':        reply_type,
            'res_id':            parent_msg.res_id,
            'res_model':         parent_msg.model,
        })

        # 2. Actual chatter me bhi message post karo
        #    taaki chatter me dikh sake
        record = self.env[parent_msg.model].browse(parent_msg.res_id)
        record.message_post(
            body=body,
            message_type='comment',
            subtype_xmlid='mail.mt_comment' if reply_type == 'comment' else 'mail.mt_note',
            parent_id=parent_message_id,
        )

        return reply.id

    @api.model
    def get_replies(self, parent_message_id):
        """
        Kisi bhi parent message ki saari replies return karta hai.
        JS component is method ko call karega.
        """
        replies = self.search([
            ('parent_message_id', '=', parent_message_id)
        ])

        return replies.read([
            'body',
            'reply_type',
            'author_id',
            'create_date',
        ])