/** @odoo-module **/
import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/store/pos_store";
import { LotSelectionPopup } from "@inom_pos_product_by_lot_number/js/popups/lot_selection_popup";

/**
 * PATCH: PosStore — Odoo 19 compatible
 *
 * KEY FIX: Odoo 19 PosStore does NOT have `this.orm`.
 * All RPC calls must use `this.data.call(model, method, [args])`.
 * `this.data` is the pos_data service injected in setup().
 * `this.models` is shortcut for `this.data.models`.
 * `this.notification` and `this.dialog` are available directly.
 */
patch(PosStore.prototype, {

    // ─────────────────────────────────────────────────────────────────
    // CONFIG HELPERS
    // ─────────────────────────────────────────────────────────────────

    _iml_lotPopupEnabled() {
        try {
            const cfg = this.config;
            if (cfg && cfg.iml_enable_lot_popup === false) return false;
        } catch (e) {}
        return true;
    },

    // ─────────────────────────────────────────────────────────────────
    // PRODUCT / TRACKING RESOLUTION
    // ─────────────────────────────────────────────────────────────────

    _iml_resolveProduct(vals, opts = {}) {
        let product = vals?.product_id || opts?.presetVariant || null;

        let template = vals?.product_tmpl_id || null;
        if (typeof template === "number") {
            template = this.models?.["product.template"]?.get?.(template) || null;
        }
        if (!template && product) {
            template = product.product_tmpl_id || null;
        }
        if (!product && template) {
            product = opts?.presetVariant
                || template.product_variant_ids?.[0]
                || null;
        }
        return { product, template };
    },

    _iml_isTracked(template, product) {
        // Odoo 18 defines isTracked() on product.product; prefer it when present.
        if (product && typeof product.isTracked === "function") {
            try { return product.isTracked(); } catch (e) {}
        }
        const tmpl = template || product?.product_tmpl_id;
        if (tmpl && typeof tmpl.isTracked === "function") {
            try { return tmpl.isTracked(); } catch (e) {}
        }
        const tracking = tmpl?.tracking ?? product?.tracking;
        return !!tracking && tracking !== "none";
    },

    // ─────────────────────────────────────────────────────────────────
    // CORE INTERCEPT: addLineToCurrentOrder
    // ─────────────────────────────────────────────────────────────────

    async addLineToCurrentOrder(vals, opts = {}, configure = true) {
        const { product, template } = this._iml_resolveProduct(vals, opts);
        const isTracked = this._iml_isTracked(template, product);

        // Fast path: lot already chosen via barcode scan
        if (opts?.iml_pre_selected_lot && product && isTracked) {
            const preLot = opts.iml_pre_selected_lot;
            const line = await super.addLineToCurrentOrder(vals, opts, false);
            if (line) {
                this._iml_applyLotsToLine(
                    line,
                    { lots: [{ lot_name: preLot.lot_name, qty: preLot.qty || 1 }] },
                    product,
                );
            }
            return line;
        }

        // Intercept tracked products to show custom popup
        const shouldIntercept =
            configure &&
            !opts?.iml_skip_lot_popup &&
            product &&
            isTracked &&
            this._iml_lotPopupEnabled();

        if (!shouldIntercept) {
            return await super.addLineToCurrentOrder(vals, opts, configure);
        }

        const cachedLots  = await this._iml_getCachedLotsForProduct(product);
        const usedInOrder = this._iml_collectUsedQtyForProduct(product);

        const result = await this._iml_promptLotSelection(
            product, cachedLots, [], usedInOrder,
        );
        if (!result?.confirmed || !result.lots?.length) {
            return null;
        }

        // configure=false skips Odoo's own lot popup
        const line = await super.addLineToCurrentOrder(vals, opts, false);
        if (line) {
            this._iml_applyLotsToLine(line, result, product);
        }
        return line;
    },

    // ─────────────────────────────────────────────────────────────────
    // BARCODE LOT HANDLER
    // Called from ProductScreen when barcode type is 'error' or 'product'
    // ─────────────────────────────────────────────────────────────────

    async iml_handleLotBarcode(barcode) {
        if (this.config?.iml_enable_lot_scanning === false) return false;

        // Build candidate strings — barcode may be string or parsed object
        let candidates = [];
        if (typeof barcode === "string" || typeof barcode === "number") {
            candidates = [String(barcode)];
        } else if (barcode && typeof barcode === "object") {
            candidates = [barcode.base_code, barcode.code, barcode.value];
        }
        candidates = [
            ...new Set(
                candidates
                    .map(c => (c === undefined || c === null ? "" : String(c).trim()))
                    .filter(Boolean)
            ),
        ];
        if (!candidates.length) return false;

        // Try each candidate — use this.data.call (Odoo 19, NOT this.orm.call)
        let info = false;
        for (const text of candidates) {
            try {
                info = await this.data.call(
                    "stock.lot",
                    "get_product_and_lot_by_barcode",
                    [text],
                );
            } catch (err) {
                console.warn("[iml_pos_lot] barcode RPC failed:", err);
                return false;
            }
            if (info && info.product_id) break;
            info = false;
        }
        if (!info || !info.product_id) return false;

        // Resolve product from POS model cache
        const product = this.models?.["product.product"]?.get?.(info.product_id)
            || this.models?.["product.product"]?.find?.(p => p.id === info.product_id);

        if (!product) {
            console.warn("[iml_pos_lot] product not in POS cache, id:", info.product_id);
            return false;
        }

        await this.addLineToCurrentOrder(
            { product_id: product, product_tmpl_id: product.product_tmpl_id },
            { iml_pre_selected_lot: { lot_name: info.lot_name, qty: 1 } },
        );

        this.notification?.add?.(
            `${product.display_name}: lot ${info.lot_name} added`,
            { type: "success" },
        );
        return true;
    },

    // ─────────────────────────────────────────────────────────────────
    // CREATE LOT FROM POS — uses this.data.call (Odoo 19)
    // ─────────────────────────────────────────────────────────────────

    async iml_createLotFromPos(vals) {
        try {
            return await this.data.call("stock.lot", "create_lot_from_pos", [vals]);
        } catch (err) {
            throw err;
        }
    },

    // ─────────────────────────────────────────────────────────────────
    // LOT CACHE
    // ─────────────────────────────────────────────────────────────────

    async _iml_getCachedLotsForProduct(product) {
        let lots = [];
        try {
            // Try live fetch first — uses this.data.call (Odoo 19)
            const fresh = await this.data.call(
                "stock.lot",
                "get_lots_by_product",
                [product.id],
            );
            if (Array.isArray(fresh)) {
                lots = fresh.map(l => ({
                    id: l.id,
                    name: l.name,
                    product_qty: l.product_qty ?? 0,
                    expiration_date: l.expiration_date || false,
                }));
            }
        } catch (e) {
            // Offline fallback: use whatever is in POS model cache
            try {
                const lotModel = this.models?.["stock.lot"];
                const all = (typeof lotModel?.getAll === "function")
                    ? lotModel.getAll()
                    : (Array.isArray(lotModel) ? lotModel : []);
                lots = all
                    .filter(l => (l.product_id?.id ?? l.product_id) === product.id)
                    .map(l => ({
                        id: l.id,
                        name: l.name,
                        product_qty: l.product_qty ?? 0,
                        expiration_date: l.expiration_date || false,
                    }));
            } catch (e2) {}
        }
        return lots;
    },

    _iml_collectUsedQtyForProduct(product) {
        const used = {};
        try {
            const order = (typeof this.getOrder === "function" ? this.getOrder() : null)
                || this.selectedOrder || null;
            if (!order) return used;
            const lines = typeof order.getOrderlines === "function"
                ? order.getOrderlines()
                : (order.lines || []);
            for (const line of lines) {
                const pid = line.product_id?.id ?? line.product_id;
                if (pid !== product.id) continue;
                const packs = line.pack_lot_ids || [];
                for (const p of packs) {
                    if (!p.lot_name) continue;
                    used[p.lot_name] = (used[p.lot_name] || 0)
                        + (line.qty ?? 1) / Math.max(packs.length, 1);
                }
            }
        } catch (err) {}
        return used;
    },

    async _iml_promptLotSelection(product, cachedLots, initialLots = [], usedInOrder = {}) {
        return await new Promise((resolve) => {
            this.dialog.add(LotSelectionPopup, {
                product,
                cachedLots,
                initialLots,
                usedInOrder,
                getPayload: resolve,
            });
        });
    },

    _iml_applyLotsToLine(line, result, product) {
        const PackLot = this.models?.["pos.pack.operation.lot"];
        if (!PackLot || typeof PackLot.create !== "function") {
            console.warn("[iml_pos_lot] pos.pack.operation.lot model not available");
            return;
        }
        for (const { lot_name } of result.lots) {
            try {
                PackLot.create({ pos_order_line_id: line, lot_name });
            } catch (err) {
                console.warn(`[iml_pos_lot] failed to attach lot "${lot_name}":`, err);
            }
        }
        const totalQty = result.totalQty
            || result.lots.reduce((s, l) => s + (l.qty || 1), 0);
        const targetQty = product.tracking === "serial" ? 1 : totalQty;
        // Orderline qty setter differs by version: Odoo 19 exposes
        // setQuantity()/set_unit_qty(); Odoo 18 exposes set_quantity().
        // Try each in turn, then fall back to a direct (reactive) assignment.
        if (typeof line.set_unit_qty === "function") {
            line.set_unit_qty(targetQty);
        } else if (typeof line.setQuantity === "function") {
            line.setQuantity(targetQty);
        } else if (typeof line.set_quantity === "function") {
            line.set_quantity(targetQty);
        } else {
            line.qty = targetQty;
        }
    },
});
