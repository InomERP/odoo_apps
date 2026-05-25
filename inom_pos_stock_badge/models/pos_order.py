# -*- coding: utf-8 -*-
from odoo import models
import logging

_logger = logging.getLogger(__name__)


class PosOrder(models.Model):
    _inherit = 'pos.order'

    def _create_order_picking(self):

        self.ensure_one()
        session = self.session_id


        skip_real_time = (
            session.update_stock_at_closing
            and not (self.company_id.anglo_saxon_accounting and self.to_invoice)
        )

        if not skip_real_time:

            return super()._create_order_picking()


        try:
            session.sudo().write({'update_stock_at_closing': False})
            _logger.info(
                "[Inom POS Stock] Forcing real-time picking for order %s "
                "(session %s was in closing mode)",
                self.name, session.name,
            )
            return super()._create_order_picking()
        finally:
            session.sudo().write({'update_stock_at_closing': True})