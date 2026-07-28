# -*- coding: utf-8 -*-
from markupsafe import Markup, escape

from odoo import api, fields, models, _
from odoo.tools.misc import formatLang


class InomCostEstimate(models.Model):
    _inherit = 'inom.cost.estimate'

    cost_sheet_html = fields.Html(
        string='Cost Sheet', compute='_compute_cost_sheet_html', sanitize=False)

    # Each bucket: (label, field name, colour). Adding a new cost bucket later
    # (equipment, subcontract, ...) means adding one tuple here and nothing else.
    def _get_cost_sheet_buckets(self):
        return [
            (_('Materials'), 'amount_material', '#3C7CFF'),
            (_('Manpower'), 'amount_labour', '#22B07D'),
            (_('Equipment'), 'amount_equipment', '#8B5CF6'),
            (_('Indirect Cost'), 'amount_overhead', '#F2A93B'),
        ]

    def _get_internal_sections(self):
        """Line groups for the internal cost sheet, in presentation order."""
        self.ensure_one()
        return [
            {'title': _('Materials'), 'lines': self.material_line_ids},
            {'title': _('Manpower'), 'lines': self.labour_line_ids},
            {'title': _('Equipment'), 'lines': self.equipment_line_ids},
            {'title': _('Indirect Cost'), 'lines': self.overhead_line_ids},
        ]

    def _build_benchmark_badge(self):
        """Flag a job that is priced well away from comparable ones.

        Stays quiet under three comparables and under a 10% gap, so it means
        something when it does appear.
        """
        self.ensure_one()
        if self.similar_count < 3 or abs(self.cost_gap_percent) < 10.0:
            return Markup('')
        over = self.cost_gap_percent > 0
        return Markup(
            '<span class="inom_cs_badge %s">%s</span>'
        ) % ('inom_cs_badge_hi' if over else 'inom_cs_badge_lo',
             escape(_('%(pct).0f%% %(dir)s similar jobs',
                      pct=abs(self.cost_gap_percent),
                      dir=_('above') if over else _('below'))))

    def _format_money(self, amount):
        self.ensure_one()
        return formatLang(
            self.env, amount or 0.0, currency_obj=self.currency_id)

    def _build_cost_sheet_rows(self):
        """Return the bucket rows as dicts, shared by the form and the PDF."""
        self.ensure_one()
        total = self.amount_cost or 0.0
        rows = []
        for label, fname, colour in self._get_cost_sheet_buckets():
            amount = self[fname] or 0.0
            rows.append({
                'label': label,
                'amount': amount,
                'colour': colour,
                'share': (amount / total * 100.0) if total else 0.0,
            })
        return rows

    def _build_cost_sheet_donut(self, rows):
        """Pure-CSS donut. No chart library, so nothing to load or break."""
        stops, cursor = [], 0.0
        for row in rows:
            if row['share'] <= 0:
                continue
            start, cursor = cursor, cursor + row['share']
            stops.append('%s %.2f%% %.2f%%' % (row['colour'], start, cursor))
        if not stops:
            stops = ['#D9DDE3 0% 100%']
        return Markup(
            '<div class="inom_cs_donut" style="background:conic-gradient(%s)">'
            '<div class="inom_cs_donut_hole"></div></div>'
        ) % Markup(', '.join(stops))

    @api.depends('amount_material', 'amount_labour', 'amount_overhead',
                 'amount_cost', 'markup_percent', 'amount_sell',
                 'amount_margin', 'margin_percent', 'amount_tax',
                 'amount_total', 'currency_id')
    def _compute_cost_sheet_html(self):
        for rec in self:
            rows = rec._build_cost_sheet_rows()

            bars = Markup('')
            for row in rows:
                bars += Markup(
                    '<div class="inom_cs_row">'
                    '<div class="inom_cs_row_head">'
                    '<span class="inom_cs_dot" style="background:%s"></span>'
                    '<span class="inom_cs_label">%s</span>'
                    '<span class="inom_cs_amount">%s</span>'
                    '</div>'
                    '<div class="inom_cs_track">'
                    '<div class="inom_cs_fill" style="width:%.2f%%;background:%s"></div>'
                    '</div>'
                    '</div>'
                ) % (
                    row['colour'], escape(row['label']),
                    escape(rec._format_money(row['amount'])),
                    row['share'], row['colour'],
                )

            profit_label = _('Profit (markup %(mk).2f%% / margin %(mg).2f%%)') % {
                'mk': rec.markup_percent or 0.0,
                'mg': rec.margin_percent or 0.0,
            }

            return_html = Markup(
                '<div class="inom_cs">'
                '  <div class="inom_cs_head">%(title)s%(badge)s</div>'
                '  <div class="inom_cs_body">'
                '    <div class="inom_cs_chart">%(donut)s</div>'
                '    <div class="inom_cs_bars">%(bars)s</div>'
                '  </div>'
                '  <div class="inom_cs_totals">'
                '    <div class="inom_cs_line"><span>%(cost_label)s</span>'
                '      <span class="inom_cs_val">%(cost)s</span></div>'
                '    <div class="inom_cs_line"><span>%(profit_label)s</span>'
                '      <span class="inom_cs_val inom_cs_pos">%(profit)s</span></div>'
                '    %(discount_row)s'
                '    <div class="inom_cs_line inom_cs_sub"><span>%(sell_label)s</span>'
                '      <span class="inom_cs_val">%(sell)s</span></div>'
                '    <div class="inom_cs_line inom_cs_sub"><span>%(tax_label)s</span>'
                '      <span class="inom_cs_val">%(tax)s</span></div>'
                '    %(rounding_row)s'
                '    <div class="inom_cs_final"><span>%(final_label)s</span>'
                '      <span class="inom_cs_val">%(final)s</span></div>'
                '  </div>'
                '</div>'
            ) % {
                'title': escape(_('Project Cost Summary')),
                'badge': rec._build_benchmark_badge(),
                'donut': rec._build_cost_sheet_donut(rows),
                'bars': bars,
                'cost_label': escape(_('Total Cost')),
                'cost': escape(rec._format_money(rec.amount_cost)),
                'profit_label': escape(profit_label),
                'profit': escape(rec._format_money(rec.amount_margin)),
                'discount_row': (Markup(
                    '<div class="inom_cs_line inom_cs_sub"><span>%s</span>'
                    '<span class="inom_cs_val">-%s</span></div>'
                ) % (escape(_('Discount')),
                     escape(rec._format_money(rec.amount_discount)))
                    if rec.amount_discount else Markup('')),
                'sell_label': escape(_('Selling Price')),
                'sell': escape(rec._format_money(rec.amount_sell)),
                'tax_label': escape(_('Taxes')),
                'tax': escape(rec._format_money(rec.amount_tax)),
                'rounding_row': (Markup(
                    '<div class="inom_cs_line inom_cs_sub"><span>%s</span>'
                    '<span class="inom_cs_val">%s</span></div>'
                ) % (escape(_('Rounding')),
                     escape(rec._format_money(rec.amount_rounding)))
                    if rec.amount_rounding else Markup('')),
                'final_label': escape(_('Final Price')),
                'final': escape(rec._format_money(rec.amount_total)),
            }
            rec.cost_sheet_html = return_html
