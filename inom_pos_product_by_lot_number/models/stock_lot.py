# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import AccessError, ValidationError


class StockLot(models.Model):
    """
    Core server-side model for the POS Lot module.

    Adds (Phases 1-6 combined):
      * `iml_pos_used_count`         — stat-button counter on the lot form
      * RPC methods consumed by the POS frontend:
          - get_lots_by_product            (Phase 2: popup list)
          - get_lot_by_name                (Phase 2: manual entry)
          - search_lots_autocomplete       (Phase 2: autocomplete)
          - get_product_and_lot_by_barcode (Phase 3: scanner)
          - create_lot_from_pos            (Phase 4: in-POS lot creation)
          - sync_offline_lot_creates       (Phase 5: batch reconnect-sync)
          - check_serial_used              (Phase 4: duplicate-serial check)
    """
    _inherit = 'stock.lot'

    # ─────────────────────────────────────────────────────────────────────
    # FIELDS
    # ─────────────────────────────────────────────────────────────────────

    iml_pos_used_count = fields.Integer(
        string="POS Sales Count",
        compute='_compute_iml_pos_used_count',
        help="Number of POS order lines that used this lot/serial.",
    )

    def _compute_iml_pos_used_count(self):
        """Count POS lines referencing this lot by name+product."""
        PackLot = self.env['pos.pack.operation.lot'].sudo()
        for lot in self:
            if not lot.name or not lot.product_id:
                lot.iml_pos_used_count = 0
                continue
            lot.iml_pos_used_count = PackLot.search_count([
                ('lot_name', '=', lot.name),
                ('pos_order_line_id.product_id', '=', lot.product_id.id),
            ])

    # ─────────────────────────────────────────────────────────────────────
    # PUBLIC RPC METHODS  (consumed on demand by the POS frontend)
    # ─────────────────────────────────────────────────────────────────────

    @api.model
    def get_lots_by_product(self, product_id, limit=100):
        """Return available lots for a product. Used by the popup."""
        if not product_id or not isinstance(product_id, int):
            return []
        domain = [
            ('product_id', '=', product_id),
            ('product_qty', '>', 0),
            ('company_id', 'in', (False, self.env.company.id)),
        ]
        return self.search_read(
            domain=domain,
            fields=['id', 'name', 'product_id', 'product_qty',
                    'expiration_date', 'ref'],
            limit=max(1, min(int(limit or 100), 500)),
            order='expiration_date asc, name asc',
        )

    @api.model
    def get_lot_by_name(self, name, product_id=False):
        """Exact lookup by lot name."""
        if not name or not isinstance(name, str):
            return False
        domain = [
            ('name', '=', name.strip()),
            ('company_id', 'in', (False, self.env.company.id)),
        ]
        if product_id and isinstance(product_id, int):
            domain.append(('product_id', '=', product_id))
        result = self.search_read(
            domain=domain,
            fields=['id', 'name', 'product_id', 'product_qty', 'expiration_date'],
            limit=1,
        )
        return result[0] if result else False

    @api.model
    def search_lots_autocomplete(self, term, product_id=False, limit=20):
        """Fuzzy lot-name search for autocomplete."""
        if not term or not isinstance(term, str):
            return []
        term = term.strip()
        if not term:
            return []
        domain = [
            ('name', 'ilike', term),
            ('product_qty', '>', 0),
            ('company_id', 'in', (False, self.env.company.id)),
        ]
        if product_id and isinstance(product_id, int):
            domain.append(('product_id', '=', product_id))
        return self.search_read(
            domain=domain,
            fields=['id', 'name', 'product_id', 'product_qty', 'expiration_date'],
            limit=max(1, min(int(limit or 20), 50)),
            order='name asc',
        )

    # ─────────────────────────────────────────────────────────────────────
    # PHASE 3: Barcode scan single-call lookup  ← BUG FIX: was mis-indented
    # ─────────────────────────────────────────────────────────────────────

    @api.model
    def get_product_and_lot_by_barcode(self, barcode):
        """
        Single-call helper for the POS barcode scanner (Phase 3).
        Given a scanned barcode, returns the product+lot info so the
        frontend can auto-add the product with lot pre-assigned.

        Resolution priority:
          1. Direct match (qty > 0): stock.lot.name == barcode
          2. ref-field match (qty > 0): stock.lot.ref == barcode
          3. Fallback (any qty): lot.name or lot.ref match
             (covers lots just created from the POS that may have qty=0)
        Returns:
          { 'lot_id', 'lot_name', 'product_id', 'product_display_name',
            'product_qty', 'tracking' }
          ... or False if no match.
        """
        if not barcode or not isinstance(barcode, str):
            return False
        barcode = barcode.strip()
        if not barcode:
            return False

        company_filter = ('company_id', 'in', (False, self.env.company.id))

        lot = (
            self.search([('name', '=', barcode), ('product_qty', '>', 0), company_filter], limit=1)
            or self.search([('ref', '=', barcode), ('product_qty', '>', 0), company_filter], limit=1)
            or self.search([('name', '=', barcode), company_filter], limit=1)
            or self.search([('ref', '=', barcode), company_filter], limit=1)
        )

        if not lot:
            return False

        product = lot.product_id
        if not product or product.tracking == 'none':
            return False

        return {
            'lot_id': lot.id,
            'lot_name': lot.name,
            'product_id': product.id,
            'product_display_name': product.display_name,
            'product_qty': lot.product_qty,
            'tracking': product.tracking,
        }

    # ─────────────────────────────────────────────────────────────────────
    # PHASE 4: Create lot from POS (with security)
    # ─────────────────────────────────────────────────────────────────────

    @api.model
    def create_lot_from_pos(self, vals):
        """Create a new lot from POS. Group-protected, idempotent."""
        if not self.env.user.has_group(
            'inom_pos_product_by_lot_number.group_pos_lot_create'
        ):
            raise AccessError(
                "You are not allowed to create Lot/Serial numbers from POS."
            )

        if not isinstance(vals, dict):
            raise ValidationError("Invalid payload for lot creation.")
        name = (vals.get('name') or '').strip()
        product_id = vals.get('product_id')
        if not name or not product_id:
            raise ValidationError(
                "Lot name and product are both required to create a new lot."
            )
        product = self.env['product.product'].browse(int(product_id)).exists()
        if not product:
            raise ValidationError("The product specified does not exist.")
        if product.tracking == 'none':
            raise ValidationError(
                "Cannot create a lot/serial for a non-tracked product."
            )

        existing = self.search([
            ('name', '=', name),
            ('product_id', '=', product.id),
            ('company_id', 'in', (False, self.env.company.id)),
        ], limit=1)
        if existing:
            return {
                'id': existing.id,
                'name': existing.name,
                'product_id': existing.product_id.id,
                'product_qty': existing.product_qty,
                'expiration_date': existing.expiration_date or False,
                'duplicate': True,
            }

        new_lot = self.create({
            'name': name,
            'product_id': product.id,
            'company_id': self.env.company.id,
            'ref': (vals.get('ref') or '').strip() or False,
        })
        return {
            'id': new_lot.id,
            'name': new_lot.name,
            'product_id': new_lot.product_id.id,
            'product_qty': new_lot.product_qty,
            'expiration_date': new_lot.expiration_date or False,
            'duplicate': False,
        }

    # ─────────────────────────────────────────────────────────────────────
    # PHASE 4: Duplicate-serial check (historical)
    # ─────────────────────────────────────────────────────────────────────

    @api.model
    def check_serial_used(self, lot_name, product_id):
        """Returns True if this serial already moved to a customer."""
        if not lot_name or not product_id:
            return False
        product = self.env['product.product'].browse(int(product_id)).exists()
        if not product or product.tracking != 'serial':
            return False
        lot = self.search([
            ('name', '=', lot_name.strip()),
            ('product_id', '=', product.id),
            ('company_id', 'in', (False, self.env.company.id)),
        ], limit=1)
        if not lot:
            return False
        used = self.env['stock.move.line'].sudo().search_count([
            ('lot_id', '=', lot.id),
            ('state', '=', 'done'),
            ('location_dest_id.usage', '=', 'customer'),
        ])
        return bool(used)

    # ─────────────────────────────────────────────────────────────────────
    # PHASE 5: Batch offline-sync of queued lot creations
    # ─────────────────────────────────────────────────────────────────────

    @api.model
    def sync_offline_lot_creates(self, batch):
        """
        Drains the offline queue from the frontend.

        Input:
            batch = [
                { 'client_id': '...', 'vals': {'name', 'product_id', 'ref'} },
                ...
            ]
        Output:
            { 'results': [ { 'client_id': '...', 'ok': True, 'lot': {...} }
                         | {'client_id': '...', 'ok': False, 'error': '...'} ] }
        """
        results = []
        if not isinstance(batch, list):
            return {'results': results}

        for item in batch:
            if not isinstance(item, dict):
                continue
            client_id = item.get('client_id')
            vals = item.get('vals') or {}
            try:
                lot = self.create_lot_from_pos(vals)
                results.append({
                    'client_id': client_id,
                    'ok': True,
                    'lot': lot,
                })
            except (AccessError, ValidationError) as e:
                results.append({
                    'client_id': client_id,
                    'ok': False,
                    'error': str(e),
                })
            except Exception as e:
                results.append({
                    'client_id': client_id,
                    'ok': False,
                    'error': repr(e),
                })
        return {'results': results}

    # ─────────────────────────────────────────────────────────────────────
    # BACKEND ACTIONS
    # ─────────────────────────────────────────────────────────────────────

    def action_view_pos_orders(self):
        """Stat-button action: list POS orders that consumed this lot."""
        self.ensure_one()
        PackLot = self.env['pos.pack.operation.lot'].sudo()
        pack_lots = PackLot.search([
            ('lot_name', '=', self.name),
            ('pos_order_line_id.product_id', '=', self.product_id.id),
        ])
        order_ids = pack_lots.mapped('pos_order_line_id.order_id').ids
        return {
            'name': 'POS Orders Using This Lot',
            'type': 'ir.actions.act_window',
            'res_model': 'pos.order',
            'view_mode': 'list,form',
            'domain': [('id', 'in', order_ids)],
            'context': {'create': False},
        }
