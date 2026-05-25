/** @odoo-module **/
/**
 * ════════════════════════════════════════════════════════════════════════════
 *  inom_pos_stock_badge — Real-time stock validation in POS
 *  File: static/src/js/payment_screen_patch.js
 *
 *  PURPOSE
 *  ───────
 *  Enforce two stock-related guards declared in POS Settings, both at the
 *  moment of user action AND again at order-validation time, so the cashier
 *  can NEITHER add nor complete payment for items that breach the rules:
 *
 *    Guard 1 — "Deny POS Order When Product Qty Goes Down To" (threshold)
 *      When set to a value > 0, a popup blocks the cashier as soon as the
 *      product's remaining stock would drop to or below that value.
 *      Example: threshold = 3, stock = 10 → cashier may sell down to 4 only.
 *
 *    Guard 2 — "Available Stock Exceeded"
 *      Always active when the product is stock-tracked: a popup blocks the
 *      cashier as soon as they try to add or set a quantity greater than
 *      what is physically available.
 *      Example: stock = 10, cashier tries to set qty = 11 → popup.
 *
 *  INTERCEPTION POINTS (four layers, defense in depth)
 *  ───────────────────────────────────────────────────
 *    1. ProductScreen.addProductToOrder       → product-card click
 *    2. PosStore.addLineToCurrentOrder        → configurator "Add" / barcode
 *    3. PosOrderLine.set_quantity (runtime)   → numpad / +- on cart line
 *    4. PaymentScreen.validateOrder           → final safety net at payment
 *
 *  IMPORTANT NOTES
 *  ───────────────
 *  • Odoo 17+ changed the product-type model: storable goods now report
 *    type = "consu" with the boolean `is_storable = true`. The old check
 *    `type === "consu" → skip` therefore wrongly skipped all storable
 *    products. The helper `isUntrackedProduct()` below uses the correct
 *    Odoo 19 semantics.
 *
 *  • The pos.order.line class is patched AT RUNTIME (not via static
 *    import) because the import path varies across Odoo 19 minor builds.
 *    The runtime patch reads the live instance's prototype, so it works
 *    on every build without modification.
 *
 *  • Validation calls are idempotent: a clean cart always passes; a dirty
 *    one always fails. The check is O(lines) so running it twice on the
 *    same click (ProductScreen → PosStore) costs nothing measurable and
 *    can never produce a double popup (the first failure short-circuits
 *    the second call).
 *
 *  PRESERVED EXISTING FEATURES (none of these are modified)
 *  ────────────────────────────────────────────────────────
 *    • Stock badge rendering              (pos_stock_badge.js)
 *    • 30-second stock auto-sync          (stock_sync.js)
 *    • Low Stock filter button            (low_stock_button.js)
 *    • Order summary stock column         (order_summary.js)
 *    • Navbar stock indicator             (navbar_patch.js)
 *    • All Python models, XML views, SCSS
 * ════════════════════════════════════════════════════════════════════════════
 */

import { patch } from "@web/core/utils/patch";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { PosStore } from "@point_of_sale/app/services/pos_store";
import { useService } from "@web/core/utils/hooks";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";


// ════════════════════════════════════════════════════════════════════════════
//  SECTION 1 — Internal helpers
// ════════════════════════════════════════════════════════════════════════════

/**
 * Resolve the product.template ID from a product record, a numeric ID,
 * or any of Odoo's relation-tuple shapes.
 */
function getTemplateId(product) {
    if (!product) return null;
    if (typeof product === "number") return product;
    if (typeof product === "string") return Number(product);

    const tmpl = product.product_tmpl_id;
    if (tmpl) {
        if (typeof tmpl === "object" && tmpl !== null && tmpl.id) return Number(tmpl.id);
        if (typeof tmpl === "number") return tmpl;
        if (Array.isArray(tmpl) && tmpl.length > 0) return Number(tmpl[0]);
    }
    // For records that ARE the template itself (no product_tmpl_id back-ref).
    return product.id ? Number(product.id) : null;
}

/**
 * Read a product's stock data from pos.stockMap (populated by stock_sync.js).
 * Looks up by template ID first, then by product ID as fallback.
 */
function getStockData(pos, product) {
    if (!pos || !pos.stockMap || !product) return null;

    const tmplId = getTemplateId(product);
    if (tmplId !== null) {
        const data = pos.stockMap[tmplId] ?? pos.stockMap[String(tmplId)];
        if (data !== undefined) return data;
    }
    if (typeof product === "object" && product.id) {
        const data = pos.stockMap[product.id] ?? pos.stockMap[String(product.id)];
        if (data !== undefined) return data;
    }
    return null;
}

/**
 * Pick the right numeric stock value based on the configured stock_type:
 *   - "on_hand"   → physical quantity in warehouse
 *   - "available" → on-hand minus reserved by other orders
 */
function getStock(stockData, stockType) {
    if (!stockData) return null;
    return stockType === "available"
        ? (stockData.virtual_available ?? 0)
        : (stockData.pos_qty ?? 0);
}

/**
 * Whether a product has no stock tracking at all.
 *
 * Odoo 17+ semantics: the `type` field no longer distinguishes storable
 * goods from consumables — both report "consu". The separate boolean
 * `is_storable` decides actual tracking. We therefore skip only:
 *   - services (`type === "service"`)
 *   - combo products (`type === "combo"`)
 *   - consumables explicitly marked non-storable (`is_storable === false`)
 *
 * For everything else, the `getStockData(...) === null` fallback in
 * `checkStockBeforeAdd()` handles untracked items gracefully.
 */
function isUntrackedProduct(product) {
    if (!product || typeof product !== "object") return false;
    const t = product.type || "";
    if (t === "service") return true;
    if (t === "combo")   return true;
    if (t === "consu" && product.is_storable === false) return true;
    return false;
}

/**
 * If `anyProduct` is a numeric ID, resolve it to a real product record by
 * scanning the loaded `product.template` and `product.product` collections.
 * Returns the record as-is when it's already an object.
 */
function resolveProductRecord(pos, anyProduct) {
    if (!anyProduct) return null;
    if (typeof anyProduct === "object" && (anyProduct.id || anyProduct.display_name)) {
        return anyProduct;
    }
    const id = Number(anyProduct);
    if (isNaN(id)) return null;

    const tmpl = pos?.models?.["product.template"]?.records;
    if (tmpl) {
        for (const rec of tmpl.values()) {
            if (rec.id === id) return rec;
        }
    }
    const prod = pos?.models?.["product.product"]?.records;
    if (prod) {
        for (const rec of prod.values()) {
            if (rec.id === id) return rec;
        }
    }
    return null;
}

/**
 * Return all order lines for the given order. Tolerates the different
 * shapes that PosOrder can expose across builds (`.lines` iterable,
 * `.orderlines` collection, or only the global `pos.order.line` records).
 */
function getOrderLines(pos, order) {
    if (!order) return [];

    if (order.lines) {
        let arr;
        if (Array.isArray(order.lines)) arr = order.lines;
        else if (order.lines[Symbol.iterator]) arr = [...order.lines];
        if (arr && arr.length > 0) return arr;
    }
    if (order.orderlines) {
        const models = order.orderlines.models;
        if (models && models.length > 0) return models;
        if (Array.isArray(order.orderlines) && order.orderlines.length > 0) {
            return order.orderlines;
        }
    }

    try {
        const recordsMap = pos?.models?.["pos.order.line"]?.records;
        if (recordsMap && recordsMap.size > 0) {
            const result = [];
            for (const line of recordsMap.values()) {
                const lo = line.order_id;
                if (lo === order)                                     result.push(line);
                else if (order.id   && lo?.id   === order.id)         result.push(line);
                else if (order.uuid && lo?.uuid === order.uuid)       result.push(line);
            }
            return result;
        }
    } catch (e) {
        // Defensive — fall back to empty
    }
    return [];
}

/**
 * Sum quantities of all lines in the current order that hold the same
 * product (matched by template, so variants of one configurable product
 * are aggregated). `excludeLine` is omitted from the sum — used when we
 * are validating a NEW qty for a line whose OLD qty is still part of
 * the order, so we don't double-count it.
 */
function getAlreadyOrderedQty(pos, order, product, excludeLine) {
    const lines = getOrderLines(pos, order);
    if (!lines.length) return 0;

    const targetTmplId = getTemplateId(product);
    let total = 0;
    for (const line of lines) {
        if (excludeLine && line === excludeLine) continue;
        const lineProd = line.product_id;
        if (!lineProd) continue;
        const lineTmplId = getTemplateId(lineProd);
        const sameTemplate = targetTmplId !== null && lineTmplId === targetTmplId;
        const sameProduct  = typeof lineProd === "object" && typeof product === "object"
                          && lineProd.id === product.id;
        if (sameTemplate || sameProduct) {
            total += line.qty ?? line.quantity ?? 0;
        }
    }
    return total;
}

/**
 * Show a blocking AlertDialog. Resolves the dialog service from any of
 * the locations Odoo 19 exposes it (component, env.services, or the
 * window-level cache populated in the patches' setup hooks).
 */
function showWarning(component, title, body) {
    const svc = component?.dialog
             || component?.env?.services?.dialog
             || (typeof window !== "undefined" && window.__inomDialogService);
    if (svc && typeof svc.add === "function") {
        svc.add(AlertDialog, { title, body });
    }
}


// ════════════════════════════════════════════════════════════════════════════
//  SECTION 2 — Centralised stock-validation rules
// ════════════════════════════════════════════════════════════════════════════

/**
 * Decide whether the requested operation must be blocked. Returns a popup
 * payload `{ block: true, title, body }` when blocking is required, or
 * `null` when the operation is allowed.
 *
 * @param {Object}        pos          PosStore (config + stockMap)
 * @param {Object|number} productOrId  Product record or its id
 * @param {Number}        requestedQty Qty being added/set (1 for a click)
 * @param {Object}        excludeLine  Line whose OLD qty should NOT count
 *                                     toward "already in cart" (used when
 *                                     validating a new qty on an existing
 *                                     cart line; otherwise pass null)
 */
function checkStockBeforeAdd(pos, productOrId, requestedQty, excludeLine) {
    // ── Feature globally off → no-op ────────────────────────────────────────
    if (!pos) return null;
    const cfg = pos.config;
    if (!cfg || !cfg.display_stock) return null;

    // ── Resolve product record ──────────────────────────────────────────────
    const product = resolveProductRecord(pos, productOrId);
    if (!product) return null;
    if (isUntrackedProduct(product)) return null;

    // ── Pull stock data; skip silently when product has no stock record ─────
    const stockData = getStockData(pos, product);
    if (!stockData) return null;

    const stockType = cfg.stock_type || "on_hand";
    const stock     = getStock(stockData, stockType);
    if (stock === null) return null;

    const productName  = product.display_name || product.name || "this product";
    const denyBelowQty = Number(cfg.deny_order_below_qty ?? 0);

    const order         = pos.selectedOrder || pos.currentOrder;
    const alreadyInCart = getAlreadyOrderedQty(pos, order, product, excludeLine);
    const totalAfterAdd = alreadyInCart + (Number(requestedQty) || 0);

    // ── Rule 0: cleanly handle "stock is literally zero" with a clearer msg ─
    if (stock <= 0) {
        return {
            block: true,
            title: "Out of Stock",
            body:  `"${productName}" is out of stock. ` +
                   `This product cannot be added to the order.`,
        };
    }

    // ── Rule 1: current stock already at/below the configured threshold ─────
    //    (only active when the user has set a value > 0)
    if (denyBelowQty > 0 && stock <= denyBelowQty) {
        return {
            block: true,
            title: "Stock Limit Reached",
            body:  `Cannot add "${productName}". ` +
                   `Current stock (${stock}) has reached the minimum allowed ` +
                   `quantity (${denyBelowQty}).`,
        };
    }

    // ── Rule 2: trying to add/set more than physically available ────────────
    if (totalAfterAdd > stock) {
        return {
            block: true,
            title: "Insufficient Stock",
            body:  `Cannot add more "${productName}". ` +
                   `Available stock: ${stock} unit(s)` +
                   (alreadyInCart > 0 ? `, already in cart: ${alreadyInCart}` : "") +
                   `.`,
        };
    }

    // ── Rule 3: this add would drop remaining stock to/below the threshold ──
    if (denyBelowQty > 0 && (stock - totalAfterAdd) <= denyBelowQty) {
        const remaining = stock - totalAfterAdd;
        return {
            block: true,
            title: "Stock Limit Reached",
            body:  `Cannot add "${productName}". ` +
                   `Adding this would leave only ${remaining} unit(s) — ` +
                   `at or below the minimum allowed quantity (${denyBelowQty}).`,
        };
    }

    return null;
}


// ════════════════════════════════════════════════════════════════════════════
//  SECTION 3 — Patch: ProductScreen.addProductToOrder
//  Intercepts every click on a product card.
// ════════════════════════════════════════════════════════════════════════════

patch(ProductScreen.prototype, {
    setup() {
        super.setup(...arguments);
        // Cache the dialog service. Also expose it on window so the
        // runtime-patched order-line setter (which runs OUTSIDE a component
        // context) can still surface popups.
        this.dialog = useService("dialog");
        if (typeof window !== "undefined") {
            window.__inomDialogService = this.dialog;
        }
    },

    async addProductToOrder(product) {
        try {
            const warn = checkStockBeforeAdd(this.pos, product, 1, null);
            if (warn && warn.block) {
                showWarning(this, warn.title, warn.body);
                // Returning here blocks both the line addition AND the
                // configurator dialog from opening for variant products.
                return;
            }
        } catch (e) {
            // Never break the click handler over an internal error;
            // fall through to the original behaviour.
            console.warn("[Inom POS Stock] addProductToOrder check error:", e.message);
        }
        return await super.addProductToOrder(...arguments);
    },
});


// ════════════════════════════════════════════════════════════════════════════
//  SECTION 4 — Patch: PosStore.addLineToCurrentOrder
//  (a) Safety net for paths that bypass ProductScreen.addProductToOrder
//      (configurator confirmation, barcode scans, custom integrations).
//  (b) Runtime-patches the order-line prototype the first time a line
//      record exists, so all subsequent qty edits go through our guard.
// ════════════════════════════════════════════════════════════════════════════

patch(PosStore.prototype, {
    async setup() {
        await super.setup(...arguments);
        // Try once at boot — covers paused/restored orders whose lines
        // already exist before the first interactive add.
        try { this._inomPatchOrderLineProtoIfNeeded(); } catch (e) {}
    },

    async addLineToCurrentOrder(vals, opts = {}, configure = true) {
        try {
            const anyProduct = vals?.product_id || vals?.product_tmpl_id;
            if (anyProduct) {
                const warn = checkStockBeforeAdd(this, anyProduct, 1, null);
                if (warn && warn.block) {
                    showWarning(this, warn.title, warn.body);
                    return; // Block — do not add the line
                }
            }
        } catch (e) {
            console.warn("[Inom POS Stock] addLineToCurrentOrder check error:", e.message);
        }

        const result = await super.addLineToCurrentOrder(...arguments);

        // After the first real line exists, the order-line class is
        // discoverable via its instance prototype. Patch it once.
        try { this._inomPatchOrderLineProtoIfNeeded(); } catch (e) {}

        return result;
    },

    /**
     * Idempotent runtime patch of PosOrderLine's qty setter.
     *
     * We avoid `import { PosOrderLine }` because the module path of that
     * class varies between Odoo 19 minor builds and would crash the bundle
     * with "Cannot read properties of undefined (reading 'prototype')" on
     * the unlucky ones. Instead we wait for any line record to exist, read
     * its prototype, and overlay our check there. Guarded by a flag so it
     * never runs twice. Auto-detects whether the method is exposed as
     * `set_quantity` (snake_case) or `setQuantity` (camelCase).
     */
    _inomPatchOrderLineProtoIfNeeded() {
        const collection = this.models?.["pos.order.line"];
        if (!collection) return;
        const recs = collection.records;
        if (!recs || recs.size === 0) return;

        const sample = [...recs.values()][0];
        if (!sample) return;
        const proto = Object.getPrototypeOf(sample);
        if (!proto || proto._inomQtyPatched) return;

        let methodName = null;
        if (typeof proto.set_quantity === "function")      methodName = "set_quantity";
        else if (typeof proto.setQuantity === "function")  methodName = "setQuantity";
        if (!methodName) return;

        const originalFn = proto[methodName];
        const posStore   = this;

        proto[methodName] = function (quantity, keep_price) {
            try {
                const newQty = parseFloat(quantity);
                // Only validate positive quantities. Zero / negative are
                // line-removal or refund flows handled natively by Odoo.
                if (!isNaN(newQty) && newQty > 0) {
                    const product = this.product_id
                                 || (typeof this.get_product === "function" && this.get_product());
                    if (product) {
                        const warn = checkStockBeforeAdd(posStore, product, newQty, this);
                        if (warn && warn.block) {
                            showWarning(
                                { env: posStore.env, dialog: window.__inomDialogService },
                                warn.title, warn.body
                            );
                            // Return false → cancel the qty change.
                            // The line's previous valid qty stays intact.
                            return false;
                        }
                    }
                }
            } catch (e) {
                console.warn("[Inom POS Stock] qty-setter check error:", e.message);
            }
            return originalFn.apply(this, arguments);
        };
        proto._inomQtyPatched = true;
    },
});


// ════════════════════════════════════════════════════════════════════════════
//  SECTION 5 — Patch: PaymentScreen.validateOrder
//  Final guard. Catches anything that might have slipped past the earlier
//  layers (paused orders re-loaded with now-invalid stock, third-party
//  integrations that bypass our patches, server-side stock changes since
//  the line was added, etc.).
// ════════════════════════════════════════════════════════════════════════════

patch(PaymentScreen.prototype, {
    setup() {
        super.setup(...arguments);
        this.dialog = useService("dialog");
        if (typeof window !== "undefined") {
            window.__inomDialogService = this.dialog;
        }
    },

    async validateOrder(isForceValidate) {
        const pos = this.pos;
        const cfg = pos.config;

        if (cfg.display_stock) {
            const denyBelowQty = Number(cfg.deny_order_below_qty ?? 0);
            const stockType    = cfg.stock_type || "on_hand";
            const order        = pos.selectedOrder || pos.currentOrder;
            const lines        = getOrderLines(pos, order);

            for (const line of lines) {
                const product = line.product_id;
                if (!product || isUntrackedProduct(product)) continue;

                const stockData = getStockData(pos, product);
                if (!stockData) continue;

                const stock       = getStock(stockData, stockType);
                const lineQty     = line.qty ?? line.quantity ?? 0;
                const productName = product.display_name || product.name || "this product";

                // Out of stock at payment time
                if (stock <= 0) {
                    showWarning(this, "Cannot Validate Order",
                        `"${productName}" is out of stock. ` +
                        `Please remove it from the order before completing payment.`);
                    return;
                }

                // Ordered qty greater than what is currently available
                if (lineQty > stock) {
                    showWarning(this, "Cannot Validate Order",
                        `"${productName}" — ordered ${lineQty}, only ${stock} available. ` +
                        `Please reduce the quantity before completing payment.`);
                    return;
                }

                // Completing this line would leave stock at/below threshold
                if (denyBelowQty > 0) {
                    const remaining = stock - lineQty;
                    if (remaining <= denyBelowQty) {
                        showWarning(this, "Cannot Validate Order",
                            `"${productName}" — completing this order would leave ` +
                            `${remaining} unit(s), at or below the minimum allowed ` +
                            `quantity (${denyBelowQty}). Please reduce the quantity.`);
                        return;
                    }
                }
            }
        }

        const result = await super.validateOrder(...arguments);

        // After a successful checkout, force a stock refresh so badges
        // and subsequent checks reflect the new physical stock immediately.
        setTimeout(() => {
            try { pos._syncStock && pos._syncStock(); } catch (e) {}
        }, 1500);

        return result;
    },
});
