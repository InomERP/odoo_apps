/** @odoo-module **/
import { patch } from "@web/core/utils/patch";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { PosStore } from "@point_of_sale/app/store/pos_store";
import { useService } from "@web/core/utils/hooks";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

console.log("[INOM v2] payment_screen_patch.js LOADED — build", new Date().toISOString());


// ============================================================================
//  SECTION 1 — Internal helpers
// ============================================================================

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
    return product.id ? Number(product.id) : null;
}

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

function getStock(stockData, stockType) {
    if (!stockData) return null;
    return stockType === "available"
        ? (stockData.virtual_available ?? 0)
        : (stockData.pos_qty ?? 0);
}

function isUntrackedProduct(product) {
    if (!product || typeof product !== "object") return false;
    const t = product.type || "";
    if (t === "service") return true;
    if (t === "combo")   return true;
    if (t === "consu")   return true;
    return false;
}

function resolveProductRecord(pos, anyProduct) {
    if (!anyProduct) return null;
    if (typeof anyProduct === "object" && (anyProduct.id || anyProduct.display_name)) {
        return anyProduct;
    }
    const id = Number(anyProduct);
    if (isNaN(id)) return null;

    const byId = pos?.db?.product_by_id;
    if (byId && byId[id]) return byId[id];

    return null;
}

function getOrderLines(pos, order) {
    if (!order) return [];

    if (order.orderlines) {
        try {
            const arr = [...order.orderlines];
            if (arr.length > 0) return arr;
        } catch (e) {}
    }
    return [];
}

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

function showWarning(component, title, body) {

    const dialogService =
        component?.dialog
        || component?.env?.services?.dialog;

    // FALLBACK TO BROWSER ALERT
    if (!dialogService || typeof dialogService.add !== "function") {

        console.error("[INOM] Dialog service missing");

        alert(`${title}\n\n${body}`);

        return true;
    }

    dialogService.add(AlertDialog, {
        title,
        body,
    });

    return true;
}



function blockIfOutOfStock(pos, product, popupContext, callSite = "unknown") {

    if (!pos) return false;

    const cfg = pos.config;

    if (!cfg || !cfg.display_stock) {
        return false;
    }

    if (!product) {
        return false;
    }

    if (isUntrackedProduct(product)) {
        return false;
    }

    const stockData = getStockData(pos, product);

    if (!stockData) {
        return false;
    }

    const stockType = cfg.stock_type || "on_hand";

    const stock = getStock(stockData, stockType);

    if (stock === null) {
        return false;
    }

    // STOCK AVAILABLE
    if (stock > 0) {
        return false;
    }

    // ============================
    // STOCK <= 0
    // ============================

    const productName =
        product.display_name ||
        product.name ||
        "This product";

    // SHOW POPUP ALWAYS
    showWarning(
        popupContext,
        "Out of Stock",
        `"${productName}" is out of stock.`
    );

    // =====================================
    // allow_order_out_of_stock = TRUE
    // => ALLOW PRODUCT
    // =====================================

    if (cfg.allow_order_out_of_stock) {

        console.log(
            "[INOM] OUT OF STOCK BUT ALLOWED:",
            productName
        );

        return false;
    }

    // =====================================
    // allow_order_out_of_stock = FALSE
    // => BLOCK PRODUCT
    // =====================================

    console.log(
        "[INOM] OUT OF STOCK BLOCKED:",
        productName
    );

    return true;
}


// ============================================================================
//  SECTION 3 — Existing checks (kept verbatim, gated on stock > 0)
// ============================================================================

function checkStockBeforeAdd(pos, productOrId, requestedQty, excludeLine) {
    if (!pos) return null;
    const cfg = pos.config;
    if (!cfg || !cfg.display_stock) return null;

    const product = resolveProductRecord(pos, productOrId);
    if (!product) return null;
    if (isUntrackedProduct(product)) return null;

    const stockData = getStockData(pos, product);
    if (!stockData) return null;

    const stockType = cfg.stock_type || "on_hand";
    const stock     = getStock(stockData, stockType);
    if (stock === null) return null;
    if (stock <= 0) return null;          // owned by blockIfOutOfStock

    const productName   = product.display_name || product.name || "this product";
    const denyBelowQty  = Number(cfg.deny_order_below_qty ?? 0);
    const order         = pos.selectedOrder || pos.currentOrder;
    const alreadyInCart = getAlreadyOrderedQty(pos, order, product, excludeLine);
    const totalAfterAdd = alreadyInCart + (Number(requestedQty) || 0);

    if (denyBelowQty > 0 && stock <= denyBelowQty) {
        return {
            block: true,
            title: "Stock Limit Reached",
            body:  `Cannot add "${productName}". Current stock (${stock}) has reached the minimum allowed quantity (${denyBelowQty}).`,
        };
    }

    if (totalAfterAdd > stock) {
        return {
            block: true,
            title: "Insufficient Stock",
            body:  `Cannot add more "${productName}". Available stock: ${stock} unit(s)` +
                   (alreadyInCart > 0 ? `, already in cart: ${alreadyInCart}` : "") + `.`,
        };
    }

    if (denyBelowQty > 0 && (stock - totalAfterAdd) <= denyBelowQty) {
        const remaining = stock - totalAfterAdd;
        return {
            block: true,
            title: "Stock Limit Reached",
            body:  `Cannot add "${productName}". Adding this would leave only ${remaining} unit(s) at or below the minimum allowed quantity (${denyBelowQty}).`,
        };
    }

    return null;
}

function checkStockQtyWarning(pos, productOrId, requestedQty, excludeLine) {
    if (!pos) return null;
    const cfg = pos.config;
    if (!cfg || !cfg.display_stock || !cfg.stock_qty_validation) return null;

    const product = resolveProductRecord(pos, productOrId);
    if (!product) return null;
    if (isUntrackedProduct(product)) return null;

    const stockData = getStockData(pos, product);
    if (!stockData) return null;

    const stockType = cfg.stock_type || "on_hand";
    const stock     = getStock(stockData, stockType);
    if (stock === null) return null;
    if (stock <= 0) return null;

    const productName   = product.display_name || product.name || "this product";
    const order         = pos.selectedOrder || pos.currentOrder;
    const alreadyInCart = getAlreadyOrderedQty(pos, order, product, excludeLine);
    const totalAfterAdd = alreadyInCart + (Number(requestedQty) || 0);

    if (totalAfterAdd > stock) {
        return {
            block: false,
            title: "Stock Warning",
            body:  `Ordered quantity for "${productName}" (${totalAfterAdd}) exceeds available stock (${stock} unit(s)). You may continue but stock may be insufficient.`,
        };
    }
    return null;
}


// ============================================================================
//  SECTION 4 — ProductScreen.addProductToOrder patch (click path)
// ============================================================================

patch(ProductScreen.prototype, {

    setup() {
        super.setup(...arguments);
        this.dialog = useService("dialog");
        this.notification = useService("notification");

        if (typeof window !== "undefined") {
            window.__inomDialogService = this.dialog;
            window.__inomNotificationService = this.notification;
        }
        console.log("[INOM v2] ProductScreen.setup — services wired");
    },

    async addProductToOrder(product) {
        console.log("[INOM v2] ProductScreen.addProductToOrder →", product?.display_name);

        try {
            if (blockIfOutOfStock(this.pos, product, this, "ProductScreen.addProductToOrder")) {
                return false;
            }

            const warn = checkStockBeforeAdd(this.pos, product, 1, null);
            if (warn && warn.block) {
                showWarning(this, warn.title, warn.body);
                return false;
            }

            const qtyWarn = checkStockQtyWarning(this.pos, product, 1, null);
            if (qtyWarn) {
                showWarning(this, qtyWarn.title, qtyWarn.body);
            }
        } catch (e) {
            console.warn("[INOM v2] addProductToOrder error:", e);
        }

        return await super.addProductToOrder(...arguments);
    },
});


// ============================================================================
//  SECTION 5 — PosStore patches
// ============================================================================

patch(PosStore.prototype, {

    async setup() {
        await super.setup(...arguments);
        try { this._inomPatchOrderLineProtoIfNeeded(); } catch (e) {}
        console.log("[INOM v2] PosStore.setup done — display_stock=", this.config?.display_stock,
            "allow_oos=", this.config?.allow_order_out_of_stock);
    },

    async addLineToCurrentOrder(vals, opts = {}, configure = true) {
        const tag = vals?.product_id?.display_name || vals?.product_id;
        console.log("[INOM v2] PosStore.addLineToCurrentOrder →", tag);

        try {
            const anyProduct = vals?.product_id || vals?.product_tmpl_id;
            if (anyProduct) {
                const product  = resolveProductRecord(this, anyProduct);
                const popupCtx = { env: this.env, dialog: window.__inomDialogService };

                if (product && blockIfOutOfStock(this, product, popupCtx, "PosStore.addLineToCurrentOrder")) {
                    return false;
                }

                const warn = checkStockBeforeAdd(this, anyProduct, 1, null);
                if (warn && warn.block) {
                    showWarning(popupCtx, warn.title, warn.body);
                    return false;
                }
            }
        } catch (e) {
            console.warn("[INOM v2] addLineToCurrentOrder error:", e.message);
        }

        const result = await super.addLineToCurrentOrder(...arguments);
        try { this._inomPatchOrderLineProtoIfNeeded(); } catch (e) {}
        return result;
    },

    _inomPatchOrderLineProtoIfNeeded() {
        const order = this.selectedOrder;
        if (!order || !order.orderlines) return;

        const lines = [...order.orderlines];
        if (!lines.length) return;

        const sample = lines[0];
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
                if (!isNaN(newQty) && newQty > 0) {
                    const product = this.product_id
                                 || (typeof this.get_product === "function" && this.get_product());
                    if (product) {
                        const popupCtx = { env: posStore.env, dialog: window.__inomDialogService };

                        if (blockIfOutOfStock(posStore, product, popupCtx, "Orderline.set_quantity")) {
                            const currentQty = this.qty ?? this.quantity ?? 1;
                            return originalFn.apply(this, [String(currentQty), keep_price]);
                        }

                        const warn = checkStockBeforeAdd(posStore, product, newQty, this);
                        if (warn && warn.block) {
                            showWarning(popupCtx, warn.title, warn.body);
                            const currentQty = this.qty ?? this.quantity ?? 1;
                            return originalFn.apply(this, [String(currentQty), keep_price]);
                        }

                        const qtyWarn = checkStockQtyWarning(posStore, product, newQty, this);
                        if (qtyWarn) {
                            showWarning(popupCtx, qtyWarn.title, qtyWarn.body);
                        }
                    }
                }
            } catch (e) {
                console.warn("[INOM v2] set_quantity error:", e.message);
            }
            return originalFn.apply(this, [String(quantity), keep_price]);
        };
        proto._inomQtyPatched = true;
        console.log("[INOM v2] Orderline.set_quantity patched");
    },
});

// ----- Conditionally patch addProductToCurrentOrder (newer Odoo 17.x) -----
if (typeof PosStore.prototype.addProductToCurrentOrder === "function") {
    console.log("[INOM v2] addProductToCurrentOrder exists — patching");
    patch(PosStore.prototype, {
        async addProductToCurrentOrder(product, options = {}) {
            console.log("[INOM v2] PosStore.addProductToCurrentOrder →", product?.display_name);
            try {
                const popupCtx = { env: this.env, dialog: window.__inomDialogService };
                if (blockIfOutOfStock(this, product, popupCtx, "PosStore.addProductToCurrentOrder")) {
                    return false;
                }
            } catch (e) {
                console.warn("[INOM v2] addProductToCurrentOrder error:", e.message);
            }
            return await super.addProductToCurrentOrder(...arguments);
        },
    });
} else {
    console.log("[INOM v2] addProductToCurrentOrder NOT on PosStore — skipping (normal on older 17.x)");
}


// ============================================================================
//  SECTION 6 — _syncStock (unchanged)
// ============================================================================

patch(PosStore.prototype, {

    async _syncStock() {
        try {
            console.log("[INOM v2] _syncStock START");

            let products = [];

            const fromDb = this.db?.product_by_id;
            if (fromDb && Object.keys(fromDb).length) {
                products = Object.values(fromDb);
            }

            if (!products.length && this.models?.["product.product"]) {
                const modelStore = this.models["product.product"];
                if (typeof modelStore.getAll === "function") {
                    products = modelStore.getAll();
                } else if (modelStore.records) {
                    products = Object.values(modelStore.records);
                }
            }

            if (!products.length) {
                console.error("[INOM v2] ❌ no products in POS store");
                return;
            }

            const templateIds = [
                ...new Set(
                    products.map(p => {
                        const t = p.product_tmpl_id;
                        if (Array.isArray(t)) return t[0];
                        if (t && typeof t === "object" && t.id) return t.id;
                        if (typeof t === "number") return t;
                        return null;
                    }).filter(id => id && !isNaN(id))
                )
            ];

            if (!templateIds.length) {
                console.error("[INOM v2] ❌ no template IDs");
                return;
            }

            const cfg = this.config;
            const showStockOf = cfg.show_stock_of || "all_warehouse";
            const locationId = (showStockOf === "current_session" && cfg.stock_location_id)
                ? (Array.isArray(cfg.stock_location_id) ? cfg.stock_location_id[0] : cfg.stock_location_id)
                : false;

            const result = await this.env.services.orm.call(
                "product.template",
                "get_pos_stock_by_location",
                [],
                {
                    product_ids: templateIds,
                    location_id: locationId,
                    stock_type: cfg.stock_type || "on_hand",
                }
            );

            if (!result || !result.length) {
                console.error("[INOM v2] ❌ backend empty");
                return;
            }

            for (const item of result) {
                const entry = {
                    pos_qty: typeof item.pos_qty === "number" ? item.pos_qty : 0,
                    virtual_available: typeof item.virtual_available === "number" ? item.virtual_available : 0,
                };
                this.stockMap[item.id] = entry;
                this.stockMap[String(item.id)] = entry;
            }

            if (this.stockVersion) {
                this.stockVersion.v = Date.now();
            }

            window._debugStockMap = this.stockMap;

            if (typeof window._inomNotifyBadges === "function") {
                window._inomNotifyBadges();
            }

            window.dispatchEvent(new CustomEvent("inom-stock-updated", {
                detail: { v: Date.now(), count: result.length }
            }));

            console.log("[INOM v2] ✅ stockMap refreshed =>", result.length, "products");

        } catch (e) {
            console.error("[INOM v2] _syncStock failed:", e.message, e);
        }
    },
});


// ============================================================================
//  SECTION 7 — PaymentScreen.validateOrder (final safety net)
// ============================================================================

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

                if (stock !== null && stock <= 0) {
                    if (!cfg.allow_order_out_of_stock) {
                        showWarning(this, "Cannot Validate Order",
                            `"${productName}" is out of stock. Please remove it from the order before completing payment.`);
                    }
                    return;
                }

                if (lineQty > stock) {
                    showWarning(this, "Cannot Validate Order",
                        `"${productName}" — ordered ${lineQty}, only ${stock} available. Please reduce the quantity before completing payment.`);
                    return;
                }

                if (denyBelowQty > 0) {
                    const remaining = stock - lineQty;
                    if (remaining <= denyBelowQty) {
                        showWarning(this, "Cannot Validate Order",
                            `"${productName}" — completing this order would leave ${remaining} unit(s), at or below the minimum allowed quantity (${denyBelowQty}). Please reduce the quantity.`);
                        return;
                    }
                }
            }
        }

        const result = await super.validateOrder(...arguments);

        try {
            if (typeof pos._syncStock === "function") {
                await pos._syncStock();
            }
        } catch (e) {
            console.warn("[INOM v2] post-validate sync failed:", e);
        }

        setTimeout(() => {
            try { pos._syncStock && pos._syncStock(); } catch (e) {}
        }, 1500);

        return result;
    },
});