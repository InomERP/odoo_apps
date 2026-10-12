/** @odoo-module **/
import { patch } from "@web/core/utils/patch";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { useBarcodeReader } from "@point_of_sale/app/hooks/barcode_reader_hook";

/**
 * PATCH: ProductScreen — Odoo 19 compatible
 *
 * Odoo 19 BarcodeReader._scan() looks up callbacks by parseBarcode.type.
 * Lot numbers like "0000000000029" don't match any rule → type = 'error'.
 * Core has NO 'error' handler → falls to showNotFoundNotification.
 *
 * We register an 'error' handler that tries lot resolution first.
 * We also patch '_barcodeProductAction' so even valid-EAN lot barcodes
 * are intercepted.
 */
patch(ProductScreen.prototype, {

    setup() {
        super.setup(...arguments);
        useBarcodeReader({
            error: this._imlHandleUnknownBarcode.bind(this),
        });
    },

    /**
     * Handles barcodes with type='error' (unknown to parser).
     * Tries lot/serial resolution. Falls through to "Unknown Barcode" on miss.
     */
    async _imlHandleUnknownBarcode(code) {
        const pos = this.pos;
        if (pos?.config?.iml_enable_lot_scanning) {
            try {
                const handled = await pos.iml_handleLotBarcode(code);
                if (handled) return;
            } catch (err) {
                console.warn("[iml_pos_lot] _imlHandleUnknownBarcode failed:", err);
            }
        }
        this.barcodeReader?.showNotFoundNotification?.(code);
    },

    /**
     * Override product barcode action to also try lot resolution first.
     * Covers lot barcodes that happen to pass EAN checkdigit validation.
     */
    async _barcodeProductAction(code) {
        const pos = this.pos;
        if (pos?.config?.iml_enable_lot_scanning) {
            try {
                const handled = await pos.iml_handleLotBarcode(code);
                if (handled) return;
            } catch (err) {
                console.warn("[iml_pos_lot] _barcodeProductAction lot-check failed:", err);
            }
        }
        return await super._barcodeProductAction(code);
    },
});
