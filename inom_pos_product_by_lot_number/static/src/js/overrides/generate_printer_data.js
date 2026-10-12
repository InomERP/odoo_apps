/** @odoo-module **/
import { patch } from "@web/core/utils/patch";
import { GeneratePrinterData } from "@point_of_sale/app/utils/printer/generate_printer_data";

/**
 * PATCH: GeneratePrinterData — Odoo 20
 *
 * In Odoo 20 the POS prints its receipt by rendering the server-side QWeb
 * template `point_of_sale.pos_order_receipt` with data built by this class
 * (the JS copy of the Python `pos.order.receipt`).
 *
 * Add to every line the data our "Lot / Serial #" receipt block needs
 * (receipt/pos_order_receipt.xml) — same keys as models/pos_order_receipt.py:
 *   - iml_lot_names : the lot/serial names of the line's pack lots
 *   - iml_is_serial : true when the product is tracked by serial ("SN")
 */
patch(GeneratePrinterData.prototype, {
    generateLineData() {
        return super.generateLineData().map((lineData, index) => {
            const line = this.order.lines[index];
            lineData.iml_lot_names = (line?.pack_lot_ids || []).map(
                (pl) => pl.lot_name || pl.name
            );
            lineData.iml_is_serial = line?.product_id?.tracking === "serial";
            return lineData;
        });
    },
});
