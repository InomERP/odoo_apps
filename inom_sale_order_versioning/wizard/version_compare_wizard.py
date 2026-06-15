# -*- coding: utf-8 -*-
from markupsafe import Markup, escape

from odoo import api, fields, models, _
from odoo.tools import formatLang


class InomVersionCompareWizard(models.TransientModel):
    _name = 'inom.version.compare.wizard'
    _description = 'Compare Order Versions Wizard'

    order_id = fields.Many2one(
        comodel_name='sale.order',
        string="Base Version",
        required=True,
        readonly=True,
    )
    available_order_ids = fields.Many2many(
        comodel_name='sale.order',
        compute='_compute_available_order_ids',
    )
    compare_order_id = fields.Many2one(
        comodel_name='sale.order',
        string="Compare With",
        required=True,
        domain="[('id', 'in', available_order_ids)]",
    )
    comparison_html = fields.Html(
        string="Comparison",
        compute='_compute_comparison_html',
        sanitize=False,
    )

    @api.depends('order_id')
    def _compute_available_order_ids(self):
        for wizard in self:
            if wizard.order_id:
                chain = wizard.order_id._inom_get_version_chain()
                wizard.available_order_ids = chain - wizard.order_id
            else:
                wizard.available_order_ids = False

    def _inom_aggregate_lines(self, order):
        data = {}
        for line in order.order_line.filtered(lambda l: not l.display_type):
            if not line.product_id:
                continue
            entry = data.setdefault(line.product_id.id, {
                'name': line.product_id.display_name,
                'qty': 0.0,
                'subtotal': 0.0,
            })
            entry['qty'] += line.product_uom_qty
            entry['subtotal'] += line.price_subtotal
        return data

    @api.depends('order_id', 'compare_order_id')
    def _compute_comparison_html(self):
        for wizard in self:
            if not wizard.order_id or not wizard.compare_order_id:
                wizard.comparison_html = False
                continue
            wizard.comparison_html = wizard._inom_build_comparison(
                wizard.order_id, wizard.compare_order_id)

    def _inom_money(self, amount, currency):
        return formatLang(self.env, amount, currency_obj=currency)

    def _inom_build_comparison(self, order_a, order_b):
        currency = order_a.currency_id
        data_a = self._inom_aggregate_lines(order_a)
        data_b = self._inom_aggregate_lines(order_b)
        product_ids = list(dict.fromkeys(
            list(data_a.keys()) + list(data_b.keys())))

        name_a = escape(order_a.name)
        name_b = escape(order_b.name)

        rows = Markup("")
        for pid in product_ids:
            a = data_a.get(pid)
            b = data_b.get(pid)
            label = escape((a or b)['name'])
            if a and not b:
                status = _("Added")
                badge = 'background:#d1f0d8;color:#0a6b2e;'
                qty_a = '%g' % a['qty']
                qty_b = '-'
                sub_a = self._inom_money(a['subtotal'], currency)
                sub_b = '-'
            elif b and not a:
                status = _("Removed")
                badge = 'background:#fad7d7;color:#9b1c1c;'
                qty_a = '-'
                qty_b = '%g' % b['qty']
                sub_a = '-'
                sub_b = self._inom_money(b['subtotal'], currency)
            else:
                changed = (a['qty'] != b['qty']
                           or a['subtotal'] != b['subtotal'])
                status = _("Changed") if changed else _("Same")
                badge = ('background:#fdeccd;color:#8a5a00;' if changed
                         else 'background:#eef0f2;color:#555;')
                qty_a = '%g' % a['qty']
                qty_b = '%g' % b['qty']
                sub_a = self._inom_money(a['subtotal'], currency)
                sub_b = self._inom_money(b['subtotal'], currency)
            rows += Markup(
                '<tr>'
                '<td style="padding:6px 10px;border-bottom:1px solid #eee;">%s</td>'
                '<td style="padding:6px 10px;border-bottom:1px solid #eee;text-align:center;">%s</td>'
                '<td style="padding:6px 10px;border-bottom:1px solid #eee;text-align:center;">%s</td>'
                '<td style="padding:6px 10px;border-bottom:1px solid #eee;text-align:right;">%s</td>'
                '<td style="padding:6px 10px;border-bottom:1px solid #eee;text-align:right;">%s</td>'
                '<td style="padding:6px 10px;border-bottom:1px solid #eee;text-align:center;">'
                '<span style="%s padding:2px 8px;border-radius:10px;font-size:11px;">%s</span>'
                '</td>'
                '</tr>'
            ) % (label, qty_a, qty_b, sub_a, sub_b, Markup(badge), status)

        total_a = order_a.amount_untaxed
        total_b = order_b.amount_untaxed
        diff = total_a - total_b
        diff_color = '#0a6b2e' if diff >= 0 else '#9b1c1c'
        diff_sign = '+' if diff >= 0 else ''

        return Markup(
            '<div style="font-size:13px;">'
            '<table style="width:100%%;border-collapse:collapse;margin-bottom:12px;">'
            '<thead><tr style="background:#f5f6f8;">'
            '<th style="padding:8px 10px;text-align:left;">Product</th>'
            '<th style="padding:8px 10px;text-align:center;">Qty (%s)</th>'
            '<th style="padding:8px 10px;text-align:center;">Qty (%s)</th>'
            '<th style="padding:8px 10px;text-align:right;">Subtotal (%s)</th>'
            '<th style="padding:8px 10px;text-align:right;">Subtotal (%s)</th>'
            '<th style="padding:8px 10px;text-align:center;">Status</th>'
            '</tr></thead><tbody>%s</tbody></table>'
            '<table style="width:100%%;border-collapse:collapse;">'
            '<tr>'
            '<td style="padding:6px 10px;font-weight:bold;">Untaxed Total</td>'
            '<td style="padding:6px 10px;text-align:right;">%s: %s</td>'
            '<td style="padding:6px 10px;text-align:right;">%s: %s</td>'
            '<td style="padding:6px 10px;text-align:right;font-weight:bold;color:%s;">%s%s</td>'
            '</tr></table>'
            '</div>'
        ) % (
            name_a, name_b, name_a, name_b, rows,
            name_a, self._inom_money(total_a, currency),
            name_b, self._inom_money(total_b, currency),
            Markup(diff_color), escape(diff_sign),
            self._inom_money(diff, currency),
        )
