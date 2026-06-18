# -*- coding: utf-8 -*-
from odoo import fields, models


class StockPicking(models.Model):
    """Generate a counterpart operation in the destination company when an
    inter company transfer is validated."""
    _inherit = 'stock.picking'

    created_by_intercompany = fields.Boolean(
        string="Created by Inter Company Transfer",
        copy=False,
        default=False,
        help="Technical flag set on operations generated automatically by the "
             "inter company transfer mechanism. It prevents an endless "
             "creation loop between companies.",
    )
    intercompany_source_picking_id = fields.Many2one(
        comodel_name='stock.picking',
        string="Source Operation",
        copy=False,
        index=True,
        help="Original operation, in the other company, that triggered the "
             "creation of this operation.",
    )
    intercompany_dest_picking_id = fields.Many2one(
        comodel_name='stock.picking',
        string="Counterpart Operation",
        copy=False,
        index=True,
        help="Operation automatically created in the other company.",
    )

    def _action_done(self):
        """Trigger the inter company transfer right after the operation is
        marked as done."""
        res = super()._action_done()
        for picking in self:
            picking._generate_intercompany_transfer()
        return res

    def _get_intercompany_destination_company(self):
        """Return the company linked to the operation partner, if any."""
        self.ensure_one()
        partner = self.partner_id.commercial_partner_id
        if not partner:
            return self.env['res.company']
        return self.env['res.company'].sudo().search([
            ('partner_id', '=', partner.id),
            ('id', '!=', self.company_id.id),
        ], limit=1)

    def _intercompany_should_transfer(self, dest_company):
        """Decide whether a counterpart operation must be created."""
        self.ensure_one()
        if self.created_by_intercompany or self.intercompany_dest_picking_id:
            return False
        if not dest_company or not dest_company.intercompany_transfer_enabled:
            return False
        if not dest_company.intercompany_warehouse_id:
            return False
        apply_on = dest_company.intercompany_transfer_apply_on
        code = self.picking_type_code
        if code == 'incoming' and apply_on in ('receipt', 'both'):
            return True
        if code == 'outgoing' and apply_on in ('delivery', 'both'):
            return True
        return False

    def _get_intercompany_picking_type(self, dest_company):
        """Return the counterpart picking type in the destination company."""
        self.ensure_one()
        warehouse = dest_company.intercompany_warehouse_id
        if self.picking_type_code == 'incoming':
            # The other company received goods from us, so we deliver them.
            return warehouse.out_type_id
        # The other company delivered goods to us, so we receive them.
        return warehouse.in_type_id

    def _prepare_intercompany_move_vals(self, move, dest_company, picking_type):
        """Build the counterpart move values for a single source move."""
        self.ensure_one()
        return {
            'name': move.product_id.display_name,
            'product_id': move.product_id.id,
            'product_uom_qty': move.quantity,
            'product_uom': move.product_uom.id,
            'location_id': picking_type.default_location_src_id.id,
            'location_dest_id': picking_type.default_location_dest_id.id,
            'company_id': dest_company.id,
        }

    def _prepare_intercompany_picking_vals(self, dest_company, picking_type):
        """Build the counterpart operation values."""
        self.ensure_one()
        move_vals = []
        for move in self.move_ids:
            if move.quantity <= 0:
                continue
            move_vals.append((0, 0, self._prepare_intercompany_move_vals(
                move, dest_company, picking_type)))
        return {
            'picking_type_id': picking_type.id,
            'partner_id': self.company_id.partner_id.id,
            'location_id': picking_type.default_location_src_id.id,
            'location_dest_id': picking_type.default_location_dest_id.id,
            'company_id': dest_company.id,
            'origin': self.name,
            'created_by_intercompany': True,
            'intercompany_source_picking_id': self.id,
            'move_ids': move_vals,
        }

    def _generate_intercompany_transfer(self):
        """Create the counterpart operation in the destination company."""
        self.ensure_one()
        dest_company = self._get_intercompany_destination_company()
        if not self._intercompany_should_transfer(dest_company):
            return False
        picking_type = self._get_intercompany_picking_type(dest_company)
        if not picking_type:
            return False
        vals = self._prepare_intercompany_picking_vals(
            dest_company, picking_type)
        if not vals.get('move_ids'):
            return False
        new_picking = self.env['stock.picking'].sudo().with_company(
            dest_company).create(vals)
        new_picking.action_confirm()
        new_picking.action_assign()
        self.intercompany_dest_picking_id = new_picking.id
        self.message_post(body=self.env._(
            "Counterpart operation %(picking)s automatically created in "
            "%(company)s.",
            picking=new_picking.name,
            company=dest_company.name,
        ))
        return new_picking
