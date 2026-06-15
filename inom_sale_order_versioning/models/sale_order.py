# -*- coding: utf-8 -*-
from markupsafe import Markup
from odoo import api, fields, models, _


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    inom_root_order_id = fields.Many2one(
        comodel_name='sale.order',
        string="Original Order",
        copy=False,
        index=True,
        help="Reference to the original order from which this version was created.",
    )
    inom_version_no = fields.Integer(
        string="Version No.",
        default=0,
        copy=False,
        help="Sequential number of this order version. Zero means the original order.",
    )
    inom_version_reason_type = fields.Selection(
        selection=[
            ('price', 'Price Change'),
            ('scope', 'Scope / Lines Change'),
            ('terms', 'Terms Change'),
            ('customer', 'Customer Request'),
            ('other', 'Other'),
        ],
        string="Revision Reason",
        copy=False,
        help="Reason for which this version was created.",
    )
    inom_version_reason = fields.Text(
        string="Revision Note",
        copy=False,
        help="Free text explanation for this version.",
    )
    inom_is_version = fields.Boolean(
        string="Is a Version",
        compute='_compute_inom_is_version',
        store=True,
        help="Technical flag set when the order is a version of another order.",
    )
    inom_is_latest_version = fields.Boolean(
        string="Latest Version",
        compute='_compute_inom_version_data',
        store=True,
        help="Technical flag marking the most recent version within a version chain.",
    )
    inom_latest_version_id = fields.Many2one(
        comodel_name='sale.order',
        string="Latest Version",
        compute='_compute_inom_version_data',
        store=True,
        help="The most recent order within the same version chain.",
    )
    inom_version_count = fields.Integer(
        string="Version Count",
        compute='_compute_inom_version_data',
        help="Total number of orders that belong to the same version chain.",
    )

    @api.depends('inom_root_order_id')
    def _compute_inom_is_version(self):
        for order in self:
            order.inom_is_version = bool(order.inom_root_order_id)

    @api.depends('inom_root_order_id', 'inom_version_no')
    def _compute_inom_version_data(self):
        sale_order = self.env['sale.order']
        for order in self:
            root = order.inom_root_order_id or order
            root_id = root.id if isinstance(root.id, int) else False
            if root_id:
                chain = sale_order.search([
                    '|',
                    ('id', '=', root_id),
                    ('inom_root_order_id', '=', root_id),
                ])
            else:
                chain = order
            numbers = chain.mapped('inom_version_no') or [order.inom_version_no]
            max_no = max(numbers)
            order.inom_version_count = len(chain)
            order.inom_is_latest_version = order.inom_version_no >= max_no
            latest = chain.sorted('inom_version_no')[-1:] if chain else order
            order.inom_latest_version_id = latest.id if latest else order.id

    def _inom_get_version_chain(self):
        """Return every order that belongs to the same version chain as self."""
        self.ensure_one()
        root = self.inom_root_order_id or self
        return self.env['sale.order'].search([
            '|',
            ('id', '=', root.id),
            ('inom_root_order_id', '=', root.id),
        ])

    def _inom_create_version(self, reason_type=False, reason=False):
        """Create and return a new draft version copied from the current order."""
        self.ensure_one()
        root = self.inom_root_order_id or self
        chain = self._inom_get_version_chain()
        next_no = max(chain.mapped('inom_version_no') or [0]) + 1
        new_version = self.copy({
            'inom_root_order_id': root.id,
            'inom_version_no': next_no,
            'inom_version_reason_type': reason_type or False,
            'inom_version_reason': reason or False,
            'name': '%s-V%s' % (root.name or self.name, next_no),
            'state': 'draft',
        })
        # Refresh the version flags across the whole chain.
        (chain | new_version)._compute_inom_version_data()
        body = _("Version %(new)s created from %(src)s.",
                 new=new_version.name, src=self.name)
        if reason_type:
            label = dict(self._fields['inom_version_reason_type'].selection).get(
                reason_type, reason_type)
            body += _(" Reason: %(label)s.", label=label)
        body = Markup("<p>%s</p>") % body
        if reason:
            body += Markup("<p>%s</p>") % reason
        new_version.message_post(body=body)
        return new_version

    def action_inom_open_create_wizard(self):
        """Open the wizard that asks for a revision reason before creating."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Create Version'),
            'res_model': 'inom.version.create.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_order_id': self.id},
        }

    def action_inom_view_versions(self):
        """Open the list of every order in the current version chain."""
        self.ensure_one()
        chain = self._inom_get_version_chain()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Order Versions'),
            'res_model': 'sale.order',
            'domain': [('id', 'in', chain.ids)],
            'view_mode': 'tree,form',
            'context': {'inom_show_all_versions': True},
        }

    def action_inom_open_latest(self):
        """Open the latest version of the current chain."""
        self.ensure_one()
        latest = self.inom_latest_version_id or self
        return {
            'type': 'ir.actions.act_window',
            'name': _('Latest Version'),
            'res_model': 'sale.order',
            'res_id': latest.id,
            'view_mode': 'form',
            'views': [(False, 'form')],
            'target': 'current',
        }

    def action_inom_compare_versions(self):
        """Open the comparison wizard pre-filled with the closest version."""
        self.ensure_one()
        others = self._inom_get_version_chain() - self
        default_compare = False
        if others:
            lowers = others.filtered(
                lambda o: o.inom_version_no < self.inom_version_no)
            pick = (lowers or others).sorted('inom_version_no')[-1]
            default_compare = pick.id
        return {
            'type': 'ir.actions.act_window',
            'name': _('Compare Versions'),
            'res_model': 'inom.version.compare.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_order_id': self.id,
                'default_compare_order_id': default_compare,
            },
        }

    def action_confirm(self):
        res = super().action_confirm()
        param = self.env['ir.config_parameter'].sudo().get_param(
            'inom_sale_order_versioning.auto_cancel_previous', 'False')
        if param in ('True', 'true', '1'):
            self._inom_cancel_previous_versions()
        return res

    def _inom_cancel_previous_versions(self):
        """Cancel earlier confirmed versions when a newer one is confirmed."""
        sale_order = self.env['sale.order']
        for order in self:
            if not order.inom_root_order_id:
                continue
            root = order.inom_root_order_id
            previous = sale_order.search([
                '|',
                ('id', '=', root.id),
                ('inom_root_order_id', '=', root.id),
                ('id', '!=', order.id),
                ('inom_version_no', '<', order.inom_version_no),
                ('state', '=', 'sale'),
            ])
            for prev in previous:
                if prev.invoice_ids.filtered(lambda m: m.state == 'posted'):
                    prev.message_post(body=_(
                        "A newer version (%s) was confirmed, but this order was "
                        "kept because it already has a posted invoice.")
                        % order.name)
                    continue
                try:
                    prev._action_cancel()
                    prev.message_post(body=_(
                        "Automatically cancelled because a newer version (%s) "
                        "was confirmed.") % order.name)
                except Exception:
                    prev.message_post(body=_(
                        "Could not be cancelled automatically after version %s "
                        "was confirmed. Please review it manually.")
                        % order.name)

    @api.model
    def inom_get_versioning_dashboard_data(self):
        """Aggregate live versioning statistics for the dashboard."""
        sale_order = self.env['sale.order']
        company_currency = self.env.company.currency_id

        revisions = sale_order.search([('inom_version_no', '>', 0)])
        root_orders = revisions.mapped('inom_root_order_id')
        total_chains = len(root_orders)
        total_versions = len(revisions)
        avg_versions = round(total_versions / total_chains, 1) if total_chains else 0.0

        net_change = 0.0
        top_revised = []
        for root in root_orders:
            chain = sale_order.search([
                '|', ('id', '=', root.id), ('inom_root_order_id', '=', root.id)])
            sorted_chain = chain.sorted('inom_version_no')
            latest = sorted_chain[-1]
            versions_in_chain = chain.filtered(lambda o: o.inom_version_no > 0)
            change = latest.amount_untaxed - root.amount_untaxed
            net_change += change
            top_revised.append({
                'id': latest.id,
                'name': root.name or '',
                'partner': root.partner_id.display_name or '',
                'versions': len(versions_in_chain),
                'change': change,
                'latest_total': latest.amount_untaxed,
            })
        top_revised.sort(key=lambda r: r['versions'], reverse=True)
        top_revised = top_revised[:8]

        reason_labels = dict(self._fields['inom_version_reason_type'].selection)
        reasons = []
        for reason_type, count in sale_order._read_group(
                [('inom_version_no', '>', 0)],
                ['inom_version_reason_type'],
                ['__count']):
            label = reason_labels.get(reason_type) if reason_type else _('Unspecified')
            reasons.append({'label': label or _('Unspecified'), 'value': count})

        from dateutil.relativedelta import relativedelta
        today = fields.Date.context_today(self)
        buckets = {}
        order_keys = []
        for i in range(11, -1, -1):
            month = today.replace(day=1) - relativedelta(months=i)
            key = month.strftime('%Y-%m')
            buckets[key] = {'label': month.strftime('%b'), 'value': 0}
            order_keys.append(key)
        for rev in revisions:
            if rev.create_date:
                key = rev.create_date.strftime('%Y-%m')
                if key in buckets:
                    buckets[key]['value'] += 1
        trend = [buckets[k] for k in order_keys]

        return {
            'kpis': {
                'revised_quotations': total_chains,
                'versions_created': total_versions,
                'avg_versions': avg_versions,
                'net_value_change': net_change,
            },
            'currency_symbol': company_currency.symbol or '',
            'reasons': reasons,
            'trend': trend,
            'top_revised': top_revised,
        }

    @api.model
    def web_search_read(self, domain, specification, **kwargs):
        """Optionally restrict order lists to the latest version of each chain.

        The behaviour is driven by a Sales setting. Any view that needs the full
        history can bypass the filter by passing the ``inom_show_all_versions``
        context key (the version smart button does this automatically).
        """
        if not self.env.context.get('inom_show_all_versions'):
            display_mode = self.env['ir.config_parameter'].sudo().get_param(
                'inom_sale_order_versioning.display_mode', 'all')
            if display_mode == 'latest':
                domain = (domain or []) + [('inom_is_latest_version', '=', True)]
        return super().web_search_read(domain, specification, **kwargs)
