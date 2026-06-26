# -*- coding: utf-8 -*-
from odoo import _, fields, models


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    purchase_document_count = fields.Integer(
        string='Email Documents',
        compute='_compute_purchase_document_count',
        help="Number of product and vendor documents that will be attached to "
             "the next email sent for this order.",
    )

    def _compute_purchase_document_count(self):
        for order in self:
            order.purchase_document_count = len(order._get_purchase_mail_documents())

    def _get_purchase_mail_product_documents(self):
        self.ensure_one()
        mode = self.company_id.purchase_mail_attach_mode or 'all'

        products = self.order_line.product_id
        templates = products.product_tmpl_id
        if not products and not templates:
            return self.env['product.document']

        domain = [
            '|',
            '&', ('res_model', '=', 'product.template'),
            ('res_id', 'in', templates.ids),
            '&', ('res_model', '=', 'product.product'),
            ('res_id', 'in', products.ids),
        ]
        documents = self.env['product.document'].search(domain)

        eligible = self.env['product.document']
        for doc in documents:
            state = doc.attach_on_purchase
            if state == 'never':
                continue
            if state == 'always':
                eligible |= doc
            elif mode == 'all':
                eligible |= doc
        return eligible

    def _get_purchase_mail_vendor_attachments(self):
        self.ensure_one()
        if not self.company_id.purchase_mail_attach_vendor_docs:
            return self.env['ir.attachment']
        return self.partner_id.purchase_mail_attachment_ids

    def _apply_purchase_mail_guards(self, attachments):
        self.ensure_one()
        max_count = self.company_id.purchase_mail_attach_max_count or 0
        max_mb = self.company_id.purchase_mail_attach_max_mb or 0.0
        max_bytes = max_mb * 1024 * 1024

        kept = self.env['ir.attachment']
        total = 0
        for att in attachments.sorted(key=lambda a: a.id):
            if max_count and len(kept) >= max_count:
                break
            size = att.file_size or 0
            if max_bytes and total + size > max_bytes:
                continue
            kept |= att
            total += size
        return kept

    def _get_purchase_mail_documents(self):
        self.ensure_one()
        if not self.company_id.purchase_mail_attach_enabled:
            return self.env['ir.attachment']
        if self.partner_id.disable_purchase_mail_attachment:
            return self.env['ir.attachment']

        product_attachments = self._get_purchase_mail_product_documents().ir_attachment_id
        vendor_attachments = self._get_purchase_mail_vendor_attachments()

        attachments = product_attachments | vendor_attachments
        attachments = attachments.filtered(lambda a: a.type != 'url')
        return self._apply_purchase_mail_guards(attachments)

    def _process_attachments_for_template_post(self, mail_template):
        result = {}
        parent = getattr(super(), '_process_attachments_for_template_post', None)
        if parent is not None:
            result = parent(mail_template) or {}

        if not mail_template.attach_purchase_documents:
            return result

        for order in self:
            attachments = order._get_purchase_mail_documents()
            if not attachments:
                continue
            entry = result.setdefault(order.id, {})
            entry.setdefault('attachment_ids', [])
            existing = set(entry['attachment_ids'])
            entry['attachment_ids'].extend(
                aid for aid in attachments.ids if aid not in existing)
        return result

    def action_view_purchase_mail_documents(self):
        self.ensure_one()
        documents = self._get_purchase_mail_documents()
        return {
            'name': _('Purchase Email Documents'),
            'type': 'ir.actions.act_window',
            'res_model': 'ir.attachment',
            'view_mode': 'kanban,tree,form',
            'domain': [('id', 'in', documents.ids)],
            'context': {'create': False, 'delete': False},
            'target': 'current',
        }
