/** @odoo-module **/
import { patch } from "@web/core/utils/patch";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { useBarcodeReader } from "@point_of_sale/app/barcode/barcode_reader_hook";

patch(ProductScreen.prototype, {

    setup() {
        super.setup(...arguments);
        // A Lot/Serial number is rarely a valid product barcode, so the parser
        // returns type "error" (no core callback) -> "Unknown Barcode". Register
        // fallback handlers so those scans reach our lot handler first. On a
        // genuine miss we reproduce core's not-found notification.
        useBarcodeReader({
            lot: this._imlBarcodeLotFallback,
            error: this._imlBarcodeLotFallback,
        });
    },

    async _imlBarcodeLotFallback(code) {
        const pos = this.pos || this.env?.services?.pos;
        if (pos && pos.config?.iml_enable_lot_scanning !== false) {
            try {
                const handled = await pos.iml_handleLotBarcode(code);
                if (handled) {
                    return;
                }
            } catch (err) {
                console.warn("[iml_pos_lot] barcode error:", err);
            }
        }
        this.barcodeReader?.showNotFoundNotification?.(code);
    },

    async _barcodeProductAction(code) {
        const pos = this.pos || this.env?.services?.pos;
        if (pos && pos.config?.iml_enable_lot_scanning !== false) {
            try {
                const handled = await pos.iml_handleLotBarcode(code);
                if (handled) {
                    return;
                }
            } catch (err) {
                console.warn("[iml_pos_lot] barcode error:", err);
            }
        }
        return await super._barcodeProductAction(code);
    },
});
