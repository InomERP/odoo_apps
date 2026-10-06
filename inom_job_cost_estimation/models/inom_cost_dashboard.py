# -*- coding: utf-8 -*-
import math

from dateutil.relativedelta import relativedelta
from markupsafe import Markup, escape

from odoo import api, fields, models, release, _
from odoo.tools.misc import formatLang

PALETTE = ['#3C7CFF', '#22B07D', '#8B5CF6', '#F2A93B', '#EC6A5E', '#14B8C4']

STATE_COLOURS = {
    'draft': '#98A2B3',
    'confirmed': '#3C7CFF',
    'approved': '#22B07D',
    'converted': '#8B5CF6',
    'rejected': '#EC6A5E',
}

OPEN_STATES = ('draft', 'confirmed', 'approved')


class InomCostDashboard(models.TransientModel):
    _name = 'inom.cost.dashboard'
    _description = 'Job Costing Dashboard'

    period = fields.Selection([
        ('month', 'This Month'),
        ('quarter', 'This Quarter'),
        ('year', 'This Year'),
        ('all', 'All Time'),
    ], string='Period', default='year', required=True)

    trend_range = fields.Selection([
        ('6', '6 Months'),
        ('12', '12 Months'),
        ('24', '24 Months'),
    ], string='Trend', default='12', required=True)

    display_name = fields.Char(compute='_compute_display_name')

    def _compute_display_name(self):
        for rec in self:
            rec.display_name = 'Job Costing Dashboard'

    dashboard_html = fields.Html(compute='_compute_dashboard_html',
                                 sanitize=False)

    def _period_bounds(self):
        """(start, previous_start) - previous is the same length, just before."""
        self.ensure_one()
        today = fields.Date.context_today(self)
        if self.period == 'month':
            start = today + relativedelta(day=1)
            return start, start + relativedelta(months=-1)
        if self.period == 'quarter':
            start = today + relativedelta(
                month=((today.month - 1) // 3) * 3 + 1, day=1)
            return start, start + relativedelta(months=-3)
        if self.period == 'year':
            start = today + relativedelta(month=1, day=1)
            return start, start + relativedelta(years=-1)
        return None, None

    def _get_domain(self):
        start, _prev = self._period_bounds()
        return [('date_estimate', '>=', start)] if start else []

    def _previous_domain(self):
        start, prev = self._period_bounds()
        if not start:
            return None
        return [('date_estimate', '>=', prev), ('date_estimate', '<', start)]

    def _money(self, amount):
        return formatLang(self.env, amount or 0.0,
                          currency_obj=self.env.company.currency_id)

    def _short(self, amount):
        symbol = self.env.company.currency_id.symbol or ''
        amount = amount or 0.0
        for limit, suffix in ((1e9, 'B'), (1e6, 'M'), (1e3, 'K')):
            if abs(amount) >= limit:
                return '%s%.1f%s' % (symbol, amount / limit, suffix)
        return '%s%.0f' % (symbol, amount)

    def _sparkline(self, values, colour='#3C7CFF'):
        if len(values) < 2 or not any(values):
            return Markup('')
        w, h = 120.0, 30.0
        top = max(values) or 1.0
        step = w / (len(values) - 1)
        pts = ' '.join('%.1f,%.1f' % (i * step, h - (v / top) * (h - 3))
                       for i, v in enumerate(values))
        return Markup(
            '<svg class="inom_db_spark" viewBox="0 0 %s %s"'
            ' preserveAspectRatio="none"><polyline points="%s"'
            ' style="stroke:%s"/></svg>'
        ) % (w, h, pts, colour)

    def _kpi(self, icon, label, value, hint='', accent='#3C7CFF', spark=None,
             link=''):
        tag = 'a' if link else 'div'
        href = (Markup(' href="%s"') % escape(link)) if link else Markup('')
        cls = 'inom_db_kpi inom_db_kpi_link' if link else 'inom_db_kpi'
        return Markup(
            '<%s class="%s"%s>'
            '<span class="inom_db_kpi_bar" style="background:%s"></span>'
            '<span class="inom_db_kpi_ico" style="color:%s;background:%s14">'
            '<i class="fa %s"></i></span>'
            '<span class="inom_db_kpi_value">%s</span>'
            '<span class="inom_db_kpi_label">%s</span>'
            '<span class="inom_db_kpi_hint">%s</span>%s'
            '</%s>'
        ) % (Markup(tag), cls, href, accent, accent, accent, icon,
             escape(value), escape(label), escape(hint),
             spark or Markup(''), Markup(tag))

    def _estimate_url(self, extra_domain=None):
        """A link to the Cost Estimates list, optionally pre-filtered."""
        action = self.env.ref(
            'inom_job_cost_estimation.action_inom_cost_estimate',
            raise_if_not_found=False)
        if not action:
            return ''
        if release.version_info[0] >= 18:
            return '/odoo/action-%s' % action.id
        return ('/web#action=%s&model=inom.cost.estimate&view_type=list'
                % action.id)

    def _mini(self, icon, value, label, accent='#6B7280', link=''):
        tag = 'a' if link else 'div'
        href = (Markup(' href="%s"') % escape(link)) if link else Markup('')
        cls = 'inom_db_mini inom_db_mini_link' if link else 'inom_db_mini'
        return Markup(
            '<%s class="%s"%s>'
            '<span class="inom_db_mini_ico" style="color:%s;background:%s14">'
            '<i class="fa %s"></i></span>'
            '<span><b>%s</b><small>%s</small></span></%s>'
        ) % (Markup(tag), cls, href, accent, accent, icon,
             escape(value), escape(label), Markup(tag))

    def _alert(self, level, icon, text, count=None):
        badge = (Markup('<em>%s</em>') % escape(str(count))) if count else Markup('')
        return Markup(
            '<li class="inom_db_alert inom_db_alert_%s">'
            '<i class="fa %s"></i><span>%s</span>%s</li>'
        ) % (level, icon, escape(text), badge)

    def _panel(self, title, body, subtitle='', icon='', open_=True):
        """Collapsible without a line of JavaScript - plain <details>."""
        sub = (Markup('<span class="inom_db_sub">%s</span>') % escape(subtitle)
               if subtitle else Markup(''))
        ico = (Markup('<i class="fa %s"></i>') % icon) if icon else Markup('')
        return Markup(
            '<details class="inom_db_panel"%s>'
            '<summary class="inom_db_head">%s<span>%s</span>%s</summary>'
            '<div class="inom_db_body">%s</div></details>'
        ) % (Markup(' open') if open_ else Markup(''), ico, escape(title),
             sub, body)

    def _empty(self, text):
        return Markup('<p class="inom_db_empty">%s</p>') % escape(text)

    def _delta(self, now, before, money=True):
        show = self._money(now) if money else str(int(now))
        prev = self._money(before) if money else str(int(before))
        if before:
            pct = (now - before) / abs(before) * 100.0
            cls = 'up' if pct >= 0 else 'down'
            arrow = '&#9650;' if pct >= 0 else '&#9660;'
            tag = Markup('<span class="inom_db_delta %s">%s %.0f%%</span>') % (
                cls, Markup(arrow), abs(pct))
        else:
            tag = Markup('<span class="inom_db_delta flat">&mdash;</span>')
        return Markup(
            '<div class="inom_db_cmp"><span class="inom_db_cmp_val">%s</span>%s'
            '<small>%s %s</small></div>'
        ) % (escape(show), tag, escape(_('previous')), escape(prev))

    def _donut(self, slices, centre_top='', centre_sub=''):
        total = sum(s[1] for s in slices if s[1])
        if not total:
            return self._empty(_('Nothing to chart yet.'))
        r, cx, cy = 54.0, 70.0, 70.0
        circ = 2 * math.pi * r
        arcs, legend, offset = Markup(''), Markup(''), 0.0
        for entry in slices:
            label, value, colour = entry[0], entry[1], entry[2]
            slice_icon = entry[3] if len(entry) > 3 else ''
            if not value:
                continue
            share = value / total
            length = share * circ
            arcs += Markup(
                '<circle cx="%s" cy="%s" r="%s" fill="none" stroke="%s"'
                ' stroke-width="22" stroke-dasharray="%.3f %.3f"'
                ' stroke-dashoffset="%.3f" transform="rotate(-90 %s %s)"/>'
            ) % (cx, cy, r, colour, length, circ - length, -offset, cx, cy)
            offset += length
            ico = (Markup('<u class="fa %s" style="color:%s"></u>')
                   % (slice_icon, colour)) if slice_icon else Markup('')
            legend += Markup(
                '<li><i style="background:%s"></i>%s<span>%s</span><b>%s</b></li>'
            ) % (colour, ico, escape(label),
                 escape('%s (%.0f%%)' % (
                     self._short(value) if value > 999 else int(value),
                     share * 100)))
        centre = Markup('')
        if centre_top:
            centre = Markup(
                '<text x="%s" y="%s" class="inom_db_dn_top">%s</text>'
                '<text x="%s" y="%s" class="inom_db_dn_sub">%s</text>'
            ) % (cx, cy - 2, escape(centre_top), cx, cy + 16, escape(centre_sub))
        return Markup(
            '<div class="inom_db_donut"><svg viewBox="0 0 140 140">%s%s</svg>'
            '<ul class="inom_db_legend">%s</ul></div>'
        ) % (arcs, centre, legend)

    def _area_chart(self, points):
        if not points:
            return self._empty(_('Nothing in this period yet.'))
        w, h, pad, pad_b, pad_t = 720.0, 220.0, 8.0, 26.0, 14.0
        top = max(p[1] for p in points) or 1.0
        step = (w - pad * 2) / max(len(points) - 1, 1)
        plot = h - pad_b - pad_t
        coords = [(pad + i * step, pad_t + plot - (v / top) * plot)
                  for i, (_l, v, _t) in enumerate(points)]
        line = ' '.join('%.2f,%.2f' % c for c in coords)
        area = '%.2f,%.2f %s %.2f,%.2f' % (coords[0][0], pad_t + plot, line,
                                           coords[-1][0], pad_t + plot)
        grid = Markup('')
        for frac in (0.0, 0.5, 1.0):
            y = pad_t + plot - frac * plot
            grid += Markup(
                '<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" class="inom_db_grid"/>'
                '<text x="%.1f" y="%.1f" class="inom_db_tick">%s</text>'
            ) % (pad, y, w - pad, y, w - pad, y - 4, escape(self._short(top * frac)))
        dots, labels = Markup(''), Markup('')
        every = max(len(points) // 12, 1)
        for i, ((x, y), (label, _v, tip)) in enumerate(zip(coords, points)):
            dots += Markup('<circle cx="%.2f" cy="%.2f" r="3.5"'
                           ' class="inom_db_dot"><title>%s</title></circle>'
                           ) % (x, y, escape(tip))
            if i % every == 0:
                labels += Markup('<text x="%.2f" y="%.1f" class="inom_db_xlab">'
                                 '%s</text>') % (x, h - 6, escape(label))
        return Markup(
            '<svg class="inom_db_area" viewBox="0 0 %s %s" preserveAspectRatio="none">'
            '<defs><linearGradient id="inomFill" x1="0" x2="0" y1="0" y2="1">'
            '<stop offset="0%%" stop-color="#3C7CFF" stop-opacity="0.28"/>'
            '<stop offset="100%%" stop-color="#3C7CFF" stop-opacity="0.02"/>'
            '</linearGradient></defs>%s<polygon points="%s" fill="url(#inomFill)"/>'
            '<polyline points="%s" class="inom_db_line"/>%s%s</svg>'
        ) % (w, h, grid, area, line, dots, labels)

    def _bars(self, rows, ranked=False):
        if not rows:
            return self._empty(_('Nothing to show yet.'))
        top = max(r[1] for r in rows) or 1.0
        out = Markup('')
        for i, (label, value, shown) in enumerate(rows):
            rank = (Markup('<em class="inom_db_rank">%s</em>') % (i + 1)
                    if ranked else Markup(''))
            out += Markup(
                '<li>%s<span class="inom_db_bl">%s</span>'
                '<span class="inom_db_bt"><span class="inom_db_bf"'
                ' style="width:%.2f%%;background:%s"></span></span><b>%s</b></li>'
            ) % (rank, escape(label), max(value / top * 100.0, 2.0),
                 PALETTE[i % len(PALETTE)], escape(shown))
        return Markup('<ul class="inom_db_bars">%s</ul>') % out

    def _funnel(self, by_state, labels):
        order = ['draft', 'confirmed', 'approved', 'converted']
        stages, previous = [], None
        for i, state in enumerate(order):
            count = sum(by_state.get(s, {}).get('count', 0) for s in order[i:])
            value = sum(by_state.get(s, {}).get('sell', 0.0) for s in order[i:])
            drop = ('%.0f%%' % (count / previous * 100.0)) if previous else ''
            stages.append((labels.get(state, state), count, value, drop,
                           STATE_COLOURS[state]))
            previous = count or previous
        top = max((s[1] for s in stages), default=0) or 1
        rows = Markup('')
        for label, count, value, drop, colour in stages:
            rows += Markup(
                '<li><span class="inom_db_fn_head"><span class="inom_db_fn_name">%s'
                '</span><span class="inom_db_fn_drop">%s</span></span>'
                '<span class="inom_db_fn_bar" style="width:%.1f%%;background:%s">'
                '<b>%s</b><i>%s</i></span></li>'
            ) % (escape(label), escape(drop), max(count / top * 100.0, 6.0),
                 colour, escape(str(count)), escape(self._short(value)))
        lost = by_state.get('rejected', {})
        note = Markup('')
        if lost.get('count'):
            note = Markup('<p class="inom_db_fn_lost">%s</p>') % escape(
                _('%(n)s lost, worth %(v)s', n=lost['count'],
                  v=self._short(lost.get('sell', 0.0))))
        return Markup('<ul class="inom_db_funnel">%s</ul>%s') % (rows, note)

    def _data_table(self, headers, rows):
        head = Markup('').join(
            Markup('<th%s>%s</th>') % (
                Markup(' class="inom_db_num"') if h[1] else Markup(''),
                escape(h[0])) for h in headers)
        body = Markup('')
        for row in rows:
            body += Markup('<tr>%s</tr>') % Markup('').join(
                Markup('<td%s>%s</td>') % (
                    Markup(' class="inom_db_num"') if headers[i][1]
                    else Markup(''), cell) for i, cell in enumerate(row))
        return Markup('<table class="inom_db_table"><thead><tr>%s</tr></thead>'
                      '<tbody>%s</tbody></table>') % (head, body)

    def _chip(self, state, label):
        colour = STATE_COLOURS.get(state, '#98A2B3')
        return Markup('<span class="inom_db_chip" style="background:%s1F;'
                      'color:%s">%s</span>') % (colour, colour, escape(label))

    @api.depends('period', 'trend_range')
    def _compute_dashboard_html(self):
        Estimate = self.env['inom.cost.estimate']
        today_g = fields.Date.context_today(self)
        for rec in self:
            domain = rec._get_domain()
            prev_domain = rec._previous_domain()
            labels = dict(Estimate.fields_get(['state'])['state']['selection'])

            by_state = {}
            for state, count, sell, cost, margin in Estimate._read_group(
                    domain, groupby=['state'],
                    aggregates=['__count', 'amount_sell:sum',
                                'amount_cost:sum', 'amount_margin:sum']):
                by_state[state] = {'count': count, 'sell': sell or 0.0,
                                   'cost': cost or 0.0, 'margin': margin or 0.0}

            total_count = sum(v['count'] for v in by_state.values())
            total_sell = sum(v['sell'] for v in by_state.values())
            total_cost = sum(v['cost'] for v in by_state.values())
            total_margin = sum(v['margin'] for v in by_state.values())
            won = by_state.get('converted', {})
            lost = by_state.get('rejected', {})
            decided = won.get('count', 0) + lost.get('count', 0)
            win_rate = (won.get('count', 0) / decided * 100.0) if decided else 0.0
            pipeline = sum(by_state.get(s, {}).get('sell', 0.0) for s in OPEN_STATES)
            awaiting = by_state.get('confirmed', {}).get('count', 0)
            margin_pct = (total_margin / total_sell * 100.0) if total_sell else 0.0

            soon = today_g + relativedelta(days=7)
            expiring = Estimate.search_count([
                ('date_expiry', '>=', today_g), ('date_expiry', '<=', soon),
                ('state', 'in', OPEN_STATES)])
            overdue = Estimate.search_count([
                ('date_expiry', '<', today_g), ('state', 'in', OPEN_STATES)])
            no_reason = Estimate.search_count([
                ('state', '=', 'rejected'), ('loss_reason_id', '=', False)])
            # actual_cost is a non-stored compute, so it cannot appear in a
            # domain - count the jobs that are tracking actuals instead.
            overruns = Estimate.search_count([
                ('state', '=', 'converted'),
                ('analytic_account_id', '!=', False)])
            alerts = Markup('')
            if overdue:
                alerts += rec._alert('danger', 'fa-exclamation-triangle',
                                     _('estimates are past their expiry date'),
                                     overdue)
            if expiring:
                alerts += rec._alert('warn', 'fa-clock-o',
                                     _('estimates expire within 7 days'), expiring)
            if awaiting:
                alerts += rec._alert('info', 'fa-hourglass-half',
                                     _('estimates are waiting for approval'),
                                     awaiting)
            if no_reason:
                alerts += rec._alert('warn', 'fa-question-circle',
                                     _('lost estimates have no loss reason'),
                                     no_reason)
            if overruns:
                alerts += rec._alert('info', 'fa-line-chart',
                                     _('won jobs are tracking actual cost'),
                                     overruns)
            alert_block = (Markup('<ul class="inom_db_alerts">%s</ul>') % alerts
                           if alerts else Markup(''))

            months = int(rec.trend_range or '12')
            start = today_g + relativedelta(months=-(months - 1), day=1)
            monthly = {}
            for group, sell in Estimate._read_group(
                    [('date_estimate', '>=', start)],
                    groupby=['date_estimate:month'],
                    aggregates=['amount_sell:sum']):
                key = (group.strftime('%Y-%m')
                       if hasattr(group, 'strftime') else str(group))
                monthly[key] = sell or 0.0
            points, series = [], []
            for i in range(months):
                month = start + relativedelta(months=i)
                value = monthly.get(month.strftime('%Y-%m'), 0.0)
                series.append(value)
                points.append((month.strftime('%b'), value,
                               '%s: %s' % (month.strftime('%B %Y'),
                                           rec._money(value))))

            est_url = rec._estimate_url()
            kpis = (
                rec._kpi('fa-clipboard', _('Estimates'), str(total_count),
                         _('in the selected period'), PALETTE[0],
                         rec._sparkline(series, PALETTE[0]), link=est_url)
                + rec._kpi('fa-filter', _('Pipeline Value'), rec._short(pipeline),
                           _('not yet won or lost'), PALETTE[3], link=est_url)
                + rec._kpi('fa-trophy', _('Won Value'),
                           rec._short(won.get('sell', 0.0)),
                           _('converted to quotations'), PALETTE[1],
                           rec._sparkline(series, PALETTE[1]), link=est_url)
                + rec._kpi('fa-percent', _('Win Rate'), '%.0f%%' % win_rate,
                           _('%(w)s won of %(d)s decided',
                             w=won.get('count', 0), d=decided), PALETTE[2],
                           link=est_url)
                + rec._kpi('fa-line-chart', _('Avg Margin'),
                           '%.1f%%' % margin_pct, _('across all estimates'),
                           PALETTE[5], link=est_url)
                + rec._kpi('fa-hourglass-half', _('Awaiting Approval'),
                           str(awaiting), _('confirmed, not yet approved'),
                           PALETTE[4], link=est_url)
            )

            avg_value = (total_sell / total_count) if total_count else 0.0
            revisions = Estimate.search_count(domain + [('revision', '>', 0)])
            with_takeoff = Estimate.search_count(
                domain + [('material_line_ids.use_takeoff', '=', True)])
            with_docs = Estimate.search_count(
                domain + [('document_ids', '!=', False)])
            customers_count = len(Estimate._read_group(
                domain, groupby=['partner_id'], aggregates=['__count']))
            minis = (
                rec._mini('fa-calculator', rec._short(avg_value),
                          _('Avg Estimate Value'), PALETTE[0],
                          link=rec._estimate_url())
                + rec._mini('fa-users', str(customers_count), _('Customers'),
                            PALETTE[1], link=rec._estimate_url())
                + rec._mini('fa-history', str(revisions), _('Revised'), PALETTE[2],
                            link=rec._estimate_url())
                + rec._mini('fa-arrows-alt', str(with_takeoff), _('Using Takeoff'),
                            PALETTE[3], link=rec._estimate_url())
                + rec._mini('fa-paperclip', str(with_docs), _('With Documents'),
                            PALETTE[5], link=rec._estimate_url())
                + rec._mini('fa-clock-o', str(expiring), _('Expiring in 7 Days'),
                            PALETTE[4], link=rec._estimate_url())
            )

            status = rec._donut(
                [(labels.get(s, s), by_state.get(s, {}).get('count', 0),
                  STATE_COLOURS.get(s, '#98A2B3'))
                 for s in ('draft', 'confirmed', 'approved', 'converted',
                           'rejected')],
                str(total_count), _('estimates'))

            buckets = Estimate._read_group(
                domain, groupby=[],
                aggregates=['amount_material:sum', 'amount_labour:sum',
                            'amount_equipment:sum', 'amount_overhead:sum'])
            mat, lab, eqp, ovh = (buckets[0] if buckets else (0, 0, 0, 0))
            mix = rec._donut([
                (_('Materials'), mat or 0, PALETTE[0], 'fa-cubes'),
                (_('Manpower'), lab or 0, PALETTE[1], 'fa-users'),
                (_('Equipment'), eqp or 0, PALETTE[2], 'fa-truck'),
                (_('Indirect Cost'), ovh or 0, PALETTE[3], 'fa-building-o'),
            ], rec._short(total_cost), _('total cost'))

            customers = [(p.display_name, v) for p, v in Estimate._read_group(
                domain, groupby=['partner_id'],
                aggregates=['amount_sell:sum']) if p and v]
            customers.sort(key=lambda c: c[1], reverse=True)
            top = rec._bars([(n, v, rec._short(v)) for n, v in customers[:6]],
                            ranked=True)

            losses = [(r.name if r else _('Not recorded'), c, str(c))
                      for r, c in Estimate._read_group(
                          domain + [('state', '=', 'rejected')],
                          groupby=['loss_reason_id'], aggregates=['__count'])]
            losses.sort(key=lambda r: r[1], reverse=True)
            loss_body = (rec._bars(losses[:6]) if losses
                         else rec._empty(_('Nothing lost in this period.')))

            MatLine = self.env['inom.cost.material.line']
            mat_domain = [('estimate_id.state', 'in',
                           ('approved', 'converted'))]
            if domain:
                mat_domain.append(('estimate_id.date_estimate', '>=',
                                   rec._period_bounds()[0]))
            materials = [(p.display_name, v) for p, v in MatLine._read_group(
                mat_domain, groupby=['product_id'],
                aggregates=['price_subtotal:sum']) if p and v]
            materials.sort(key=lambda m: m[1], reverse=True)
            top_mat = rec._bars([(n, v, rec._short(v))
                                 for n, v in materials[:6]], ranked=True)

            if prev_domain is not None:
                prev = Estimate._read_group(
                    prev_domain, groupby=[],
                    aggregates=['__count', 'amount_sell:sum'])
                p_count, p_sell = (prev[0] if prev else (0, 0.0))
                comparison = Markup(
                    '<div class="inom_db_cmps">'
                    '<div><h6>%s</h6>%s</div><div><h6>%s</h6>%s</div></div>'
                ) % (escape(_('Estimates')),
                     rec._delta(total_count, p_count or 0, money=False),
                     escape(_('Estimated Value')),
                     rec._delta(total_sell, p_sell or 0.0))
            else:
                comparison = rec._empty(
                    _('Pick a period other than All Time to compare.'))

            tracked = Estimate.search(
                domain + [('analytic_account_id', '!=', False)],
                order='amount_cost desc', limit=6)
            va_rows = []
            for est in tracked:
                gap = est.actual_cost - est.amount_cost
                pct = (gap / est.amount_cost * 100.0) if est.amount_cost else 0.0
                va_rows.append([
                    escape(est.name),
                    escape(rec._money(est.amount_cost)),
                    escape(rec._money(est.actual_cost)),
                    Markup('<b class="%s">%s%.1f%%</b>') % (
                        'inom_db_warn' if gap > 0 else 'inom_db_pos',
                        '+' if gap > 0 else '', pct),
                ])
            variance = (rec._data_table(
                [(_('Reference'), False), (_('Estimated'), True),
                 (_('Actual'), True), (_('Variance'), True)], va_rows)
                if va_rows else rec._empty(
                    _('Link estimates to a project to compare with actuals.')))

            cat_rows = []
            for cat, count, cost, sell, margin in Estimate._read_group(
                    domain, groupby=['category_id'],
                    aggregates=['__count', 'amount_cost:sum',
                                'amount_sell:sum', 'amount_margin:sum']):
                pct = (margin / sell * 100.0) if sell else 0.0
                cat_rows.append((sell or 0.0, [
                    escape(cat.name if cat else _('Uncategorised')),
                    escape(str(count)),
                    escape(rec._money(cost or 0.0)),
                    escape(rec._money(sell or 0.0)),
                    Markup('<b class="%s">%.1f%%</b>') % (
                        'inom_db_pos' if pct >= 15 else 'inom_db_warn', pct),
                ]))
            cat_rows.sort(key=lambda r: r[0], reverse=True)
            categories = (rec._data_table(
                [(_('Job Category'), False), (_('Count'), True), (_('Cost'), True),
                 (_('Selling'), True), (_('Margin'), True)],
                [r[1] for r in cat_rows])
                if cat_rows else rec._empty(_('No categories used yet.')))

            recent = Estimate.search(domain, order='date_estimate desc, id desc',
                                     limit=8)
            activity = (rec._data_table(
                [(_('Reference'), False), (_('Customer'), False),
                 (_('Date'), False), (_('Status'), False), (_('Total'), True)],
                [[escape(e.name), escape(e.partner_id.display_name or '-'),
                  escape(fields.Date.to_string(e.date_estimate) or '-'),
                  rec._chip(e.state, labels.get(e.state, e.state)),
                  escape(rec._money(e.amount_total))] for e in recent])
                if recent else rec._empty(_('No estimates yet.')))

            rec.dashboard_html = Markup(
                '<div class="inom_db">%(alerts)s'
                '<div class="inom_db_kpis">%(kpis)s</div>'
                '<div class="inom_db_minis">%(minis)s</div>'
                '<div class="inom_db_grid1">%(funnel)s</div>'
                '<div class="inom_db_grid2">%(status)s%(mix)s</div>'
                '<div class="inom_db_grid2">%(top)s%(loss)s</div>'
                '<div class="inom_db_grid2">%(mats)s%(cmp)s</div>'
                '<div class="inom_db_grid1">%(trend)s</div>'
                '<div class="inom_db_grid1">%(variance)s</div>'
                '<div class="inom_db_grid1">%(cats)s</div>'
                '<div class="inom_db_grid1">%(recent)s</div>'
                '<p class="inom_db_foot">%(foot)s</p></div>'
            ) % {
                'alerts': alert_block,
                'kpis': kpis,
                'minis': minis,
                'funnel': rec._panel(_('Pipeline'),
                                     rec._funnel(by_state, labels),
                                     _('estimates reaching each stage'),
                                     'fa-filter'),
                'status': rec._panel(_('Estimates by Status'), status,
                                     icon='fa-pie-chart'),
                'mix': rec._panel(_('Where the Cost Sits'), mix,
                                  icon='fa-cubes'),
                'top': rec._panel(_('Top Customers'), top,
                                  _('by estimated value'), 'fa-star'),
                'loss': rec._panel(_('Why We Lost'), loss_body,
                                   _('rejected estimates'), 'fa-thumbs-down'),
                'mats': rec._panel(_('Top Materials'), top_mat,
                                   _('on won and approved jobs'), 'fa-cubes'),
                'cmp': rec._panel(_('This Period vs Previous'), comparison,
                                  icon='fa-exchange'),
                'trend': rec._panel(_('Estimate Value by Month'),
                                    rec._area_chart(points),
                                    _('%s months') % months, 'fa-area-chart'),
                'variance': rec._panel(_('Estimated vs Actual'), variance,
                                       _('jobs linked to a project'),
                                       'fa-crosshairs'),
                'cats': rec._panel(_('Performance by Job Category'), categories,
                                   icon='fa-tags'),
                'recent': rec._panel(_('Recent Estimates'), activity,
                                     icon='fa-list'),
                'foot': escape(_(
                    'Total cost %(cost)s / selling %(sell)s / margin %(margin)s',
                    cost=rec._money(total_cost), sell=rec._money(total_sell),
                    margin=rec._money(total_margin))),
            }
