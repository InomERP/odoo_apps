# -*- coding: utf-8 -*-
from odoo import models


class PosOrderReceipt(models.AbstractModel):
    """
    Odoo 20: receipts are built from `pos.order.receipt` data and rendered with
    the server-side QWeb templates (see receipt/pos_order_receipt.xml).

    Adds to every receipt line the data our "Lot / Serial #" block needs:
      * `iml_lot_names`  - the lot/serial names of the line (pack lots)
      * `iml_is_serial`  - True for serial-tracked products ("SN"), else "Lot"

    The POS frontend builds the same keys in
    static/src/js/overrides/generate_printer_data.js.
    """
    _inherit = 'pos.order.receipt'

    def _order_receipt_generate_line_data(self):
        line_data = super()._order_receipt_generate_line_data()
        for data, line in zip(line_data, self.lines):
            data['iml_lot_names'] = [
                lot.lot_name or '' for lot in line.pack_lot_ids
            ]
            data['iml_is_serial'] = line.product_id.tracking == 'serial'
        return line_data
