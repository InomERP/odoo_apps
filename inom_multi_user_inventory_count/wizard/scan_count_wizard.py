# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class StockInventoryScanWizard(models.TransientModel):
    _name = 'stock.inventory.scan.wizard'
    _description = 'Scan & Count Wizard'

    session_id = fields.Many2one(
        'stock.inventory.count.session',
        string='Session',
        required=True,
        ondelete='cascade',
    )
    # Keep progress as regular transient fields.  In Odoo 20 the scan
    # wizard is reopened in the same modal after Save & Next; relying only
    # on a non-stored relational compute can leave the Owl form showing a
    # stale cached counter even though the session line was written.
    total_count = fields.Integer(string='Total', readonly=True)
    scanned_count = fields.Integer(string='Scanned', readonly=True)
    remaining_count = fields.Integer(string='Remaining', readonly=True)
    barcode = fields.Char(
        string='Scan Barcode',
        help='Scan with the camera or a barcode gun, or type a barcode.',
    )
    current_line_id = fields.Many2one(
        'stock.inventory.session.line',
        string='Current Line',
    )
    current_product_id = fields.Many2one(
        related='current_line_id.product_id',
        string='Product',
        readonly=True,
    )
    current_location_id = fields.Many2one(
        related='current_line_id.location_id',
        string='Location',
        readonly=True,
    )
    current_qty = fields.Float(
        string='Counted Quantity',
    )
    info_message = fields.Char(
        string='Status',
        readonly=True,
    )

    def _refresh_progress(self):
        """Refresh counters from the database/session lines.

        This is deliberately explicit because Save & Next reopens the same
        transient wizard in an Owl 3 modal.
        """
        for wizard in self:
            lines = wizard.session_id.session_line_ids
            total = len(lines)
            scanned = len(lines.filtered(lambda line: line.scanned))
            wizard.write({
                'total_count': total,
                'scanned_count': scanned,
                'remaining_count': total - scanned,
            })

    @api.model
    def default_get(self, fields_list):
        vals = super().default_get(fields_list)
        session_id = vals.get('session_id') or self.env.context.get('default_session_id')
        if session_id:
            session = self.env['stock.inventory.count.session'].browse(session_id).exists()
            if session:
                lines = session.session_line_ids
                total = len(lines)
                scanned = len(lines.filtered(lambda line: line.scanned))
                vals.update({
                    'total_count': total,
                    'scanned_count': scanned,
                    'remaining_count': total - scanned,
                })
        return vals

    @api.onchange('barcode')
    def _onchange_barcode(self):
        code = (self.barcode or '').strip()
        if not code:
            return
        # Clear the input so the next scan starts fresh.
        self.barcode = False
        lines = self.env['stock.inventory.session.line'].search(
            [('session_id', '=', self.session_id.id), ('barcode', '=', code)],
            order='id asc',
        )
        if not lines:
            self.current_line_id = False
            self.info_message = _("No product matches barcode '%s'.") % code
            return
        # Prefer the first not-yet-scanned line for this barcode.  Search
        # returns a fresh recordset, so repeated scans move through each
        # location line deterministically instead of reusing a cached line.
        pending_lines = lines.filtered(lambda l: not l.scanned)
        line = pending_lines[:1]
        if not line:
            self.current_line_id = False
            self.info_message = _("All counting lines for barcode '%s' are already scanned.") % code
            return
        self.current_line_id = line.id
        self.current_qty = line.counted_qty or 0.0
        self.info_message = _("%s found at %s.") % (
            line.product_id.display_name,
            line.location_id.display_name or _("its location"))

    def _reopen(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Scan & Count'),
            'res_model': 'stock.inventory.scan.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_save_next(self):
        self.ensure_one()
        if self.current_line_id:
            line = self.current_line_id
            line.write({
                'counted_qty': self.current_qty,
                'scanned': True,
            })
            # Re-read the session lines and force the stored session counters
            # to reflect the committed line write before the modal is reopened.
            line.invalidate_recordset(['scanned', 'counted_qty'])
            self.env['stock.inventory.session.line'].flush_model(['scanned', 'counted_qty'])
            session = self.env['stock.inventory.count.session'].browse(self.session_id.id).exists()
            if session:
                session.invalidate_recordset(['session_line_ids', 'total_scanned_products', 'to_be_scanned'])
                session._compute_line_counts()
            saved = line.product_id.display_name
            self.current_line_id = False
            self.current_qty = 0.0
            self.info_message = _("Saved %s. Scan the next product.") % saved
            self._refresh_progress()
        return self._reopen()
