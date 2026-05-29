/** @odoo-module **/
import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/store/pos_store";
import { LotSelectionPopup } from "@inom_pos_product_by_lot_number/js/popups/lot_selection_popup";
import { IMLLotOfflineService } from "@inom_pos_product_by_lot_number/js/services/iml_lot_offline";

/*
 * ODOO 17 NOTES
 * -------------
 * Odoo 17 POS is the pre-`models`/`related_models` architecture. The
 * interception points differ from 18/19:
 *   - The default lot popup is shown by `getEditedPackLotLines` (called from
 *     Product.getAddProductOptions). We override that to show our custom popup.
 *   - Products are resolved through `this.db.get_product_by_id` (no this.models).
 *   - Popups use the `popup` service + AbstractAwaitablePopup, returning
 *     {confirmed, payload}.
 *   - Lots are returned as {modifiedPackLotLines, newPackLotLines}; core then
 *     applies them via orderline.setPackLotLines.
 */
patch(PosStore.prototype, {

    _iml_getOffline() {
        if (this.iml_offline === undefined) {
            try {
                this.iml_offline = new IMLLotOfflineService({
                    pos: this,
                    orm: this.orm || this.env?.services?.orm,
                });
                this.iml_offline.flushPending().catch(() => {});
            } catch (err) {
                console.warn("[iml_pos_lot] offline init failed:", err);
                this.iml_offline = null;
            }
        }
        return this.iml_offline;
    },

    _iml_lotPopupEnabled() {
        return this.config?.iml_enable_lot_popup !== false;
    },

    // Remember the product currently being added so getEditedPackLotLines
    // (which only receives the product *name*) can look up its lots.
    async addProductToCurrentOrder(product, options = {}) {
        if (Number.isInteger(product)) {
            product = this.db.get_product_by_id(product);
        }
        this._imlPendingProduct = product || null;
        try {
            return await super.addProductToCurrentOrder(product, options);
        } finally {
            this._imlPendingProduct = null;
        }
    },

    // INTERCEPTION POINT (Odoo 17): replaces the default EditListPopup.
    async getEditedPackLotLines(isAllowOnlyOneLot, packLotLinesToEdit, productName) {
        // Barcode fast path: lot already chosen by the scanner -> no popup.
        if (this._imlBarcodeLot) {
            const lot_name = this._imlBarcodeLot;
            this._imlBarcodeLot = null;
            return { modifiedPackLotLines: {}, newPackLotLines: [{ lot_name }] };
        }

        const product = this._imlPendingProduct;
        if (!this._iml_lotPopupEnabled() || !product) {
            return await super.getEditedPackLotLines(...arguments);
        }

        const usedInOrder = this._iml_collectUsedQtyForProduct(product);
        const cachedLots = await this._iml_getCachedLotsForProduct(product);

        // Odoo 17: this.popup, Odoo 18+: this.env.services.popup
        const popupService = this.popup
            || this.env?.services?.popup
            || this.env?.popup;

        if (!popupService) {
            console.error("[iml_pos_lot] popup service not found, falling back");
            return await super.getEditedPackLotLines(...arguments);
        }

        const { confirmed, payload } = await popupService.add(LotSelectionPopup, {
            product,
            cachedLots,
            usedInOrder,
            initialLots: (packLotLinesToEdit || [])
                .map((i) => ({ lot_name: i.text || i.lot_name, qty: 1 }))
                .filter((i) => i.lot_name),
        });

        if (!confirmed || !payload || !payload.lots || !payload.lots.length) {
            return; // cancelled -> abort add, exactly like the default popup
        }

        // Expand qty>1 (lot mode) into repeated pack-lot lines, mirroring core.
        const newPackLotLines = [];
        for (const l of payload.lots) {
            const n = product.tracking === "serial" ? 1 : Math.max(1, Math.round(l.qty || 1));
            for (let i = 0; i < n; i++) {
                newPackLotLines.push({ lot_name: l.lot_name });
            }
        }
        return { modifiedPackLotLines: {}, newPackLotLines };
    },

    async iml_handleLotBarcode(barcode) {
        if (this.config?.iml_enable_lot_scanning === false) return false;

        let candidates = [];
        if (typeof barcode === "string" || typeof barcode === "number") {
            candidates = [String(barcode)];
        } else if (barcode && typeof barcode === "object") {
            candidates = [barcode.base_code, barcode.code, barcode.value];
        }
        candidates = [
            ...new Set(candidates.map((c) => (c == null ? "" : String(c).trim())).filter(Boolean)),
        ];
        if (!candidates.length) return false;

        let info = false;
        for (const text of candidates) {
            try {
                info = await this.orm.call("stock.lot", "get_product_and_lot_by_barcode", [text]);
            } catch (err) {
                console.warn("[iml_pos_lot] barcode lookup failed:", err);
                return false;
            }
            if (info && info.product_id) break;
            info = false;
        }
        if (!info || !info.product_id) return false;

        const product = this.db.get_product_by_id(info.product_id);
        if (!product) return false;

        // Tell getEditedPackLotLines to skip the popup and use this lot.
        this._imlBarcodeLot = info.lot_name;
        try {
            await this.addProductToCurrentOrder(product, {});
        } finally {
            this._imlBarcodeLot = null;
        }
        this.env.services.notification?.add?.(
            `${product.display_name}: lot ${info.lot_name} added`,
            { type: "success" }
        );
        return true;
    },

    async iml_createLotFromPos(vals) {
        const off = this._iml_getOffline();
        if (off && !off.isOnline) {
            const queued = await off.queueLotCreate(vals);
            return {
                id: queued.client_id, name: vals.name, product_id: vals.product_id,
                product_qty: 0, expiration_date: false, queued: true,
            };
        }
        try {
            return await this.orm.call("stock.lot", "create_lot_from_pos", [vals]);
        } catch (err) {
            const off2 = this._iml_getOffline();
            if (off2) {
                const queued = await off2.queueLotCreate(vals);
                return {
                    id: queued.client_id, name: vals.name, product_id: vals.product_id,
                    product_qty: 0, expiration_date: false, queued: true,
                };
            }
            throw err;
        }
    },

    async _iml_getCachedLotsForProduct(product) {
        // Odoo 17 has no in-memory stock.lot model; the popup refreshes from
        // the RPC. We only seed from the offline IndexedDB cache here.
        const off = this._iml_getOffline();
        if (off) {
            try {
                return (await off.getCachedLotsForProduct(product.id)) || [];
            } catch (e) {
                /* ignore */
            }
        }
        return [];
    },

    _iml_collectUsedQtyForProduct(product) {
        const used = {};
        try {
            const order = (typeof this.get_order === "function" ? this.get_order() : null)
                || this.selectedOrder || null;
            if (!order) return used;
            const lines = (typeof order.get_orderlines === "function")
                ? order.get_orderlines()
                : (order.orderlines || []);
            for (const line of lines) {
                const lp = (typeof line.get_product === "function") ? line.get_product() : line.product;
                if (!lp || lp.id !== product.id) continue;
                const packs = (line.pack_lot_lines && line.pack_lot_lines.models)
                    || line.pack_lot_lines || [];
                for (const p of packs) {
                    const name = p.lot_name || p.get_lot_name?.();
                    if (!name) continue;
                    used[name] = (used[name] || 0) + (line.get_quantity?.() ?? line.quantity ?? 1)
                        / Math.max(packs.length, 1);
                }
            }
        } catch (err) {
            /* best-effort; popup tolerates empty */
        }
        return used;
    },
});
