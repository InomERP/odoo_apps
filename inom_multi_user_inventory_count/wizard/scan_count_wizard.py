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
    total_count = fields.Integer(
        string='Total',
        compute='_compute_progress',
    )
    scanned_count = fields.Integer(
        string='Scanned',
        compute='_compute_progress',
    )
    remaining_count = fields.Integer(
        string='Remaining',
        compute='_compute_progress',
    )
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

    @api.depends('session_id', 'session_id.session_line_ids.scanned')
    def _compute_progress(self):
        for wizard in self:
            lines = wizard.session_id.session_line_ids
            scanned = len(lines.filtered('scanned'))
            wizard.total_count = len(lines)
            wizard.scanned_count = scanned
            wizard.remaining_count = len(lines) - scanned

    @api.onchange('barcode')
    def _onchange_barcode(self):
        code = (self.barcode or '').strip()
        if not code:
            return
        # Clear the input so the next scan starts fresh.
        self.barcode = False
        lines = self.session_id.session_line_ids.filtered(
            lambda l: l.barcode and l.barcode == code)
        if not lines:
            self.current_line_id = False
            self.info_message = _("No product matches barcode '%s'.") % code
            return
        # Prefer the first not-yet-scanned line for this product.
        line = lines.filtered(lambda l: not l.scanned)[:1] or lines[:1]
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
            self.current_line_id.write({
                'counted_qty': self.current_qty,
                'scanned': True,
            })
            saved = self.current_line_id.product_id.display_name
            self.current_line_id = False
            self.current_qty = 0.0
            self.info_message = _("Saved %s. Scan the next product.") % saved
        return self._reopen()
