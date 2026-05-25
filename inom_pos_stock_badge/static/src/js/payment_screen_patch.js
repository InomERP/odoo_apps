/** @odoo-module **/
import { patch } from "@web/core/utils/patch";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { PosStore } from "@point_of_sale/app/store/pos_store";
import { useService } from "@web/core/utils/hooks";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

function getStock(pos, product) {
    if (!pos?.stockMap || !product) return null;

    const tmplId = product.product_tmpl_id?.id
        || product.product_tmpl_id
        || product.id;

    const data = pos.stockMap[tmplId] || pos.stockMap[String(tmplId)];
    if (!data) return null;

    const stockType = pos.config?.stock_type || 'on_hand';
    return stockType === 'available'
        ? (data.virtual_available ?? 0)
        : (data.pos_qty ?? 0);
}

function isService(product) {
    return !product || product.type === 'service' || product.type === 'combo';
}

function showWarning(component, title, body) {
    const svc = component?.dialog || component?.env?.services?.dialog || window.__inomDialogService;
    if (svc?.add) svc.add(AlertDialog, { title, body });
}

function getOrderLines(pos, order) {
    if (!order) return [];
    if (order.lines) {
        const arr = Array.isArray(order.lines) ? order.lines : [...order.lines];
        if (arr.length) return arr;
    }
    try {
        const all = pos.models['pos.order.line'].getAll();
        return all.filter(l => l.order_id?.id === order.id || l.order_id === order);
    } catch (e) { return []; }
}

function getAlreadyInCart(pos, order, product, excludeLine) {
    const lines = getOrderLines(pos, order);
    let total = 0;
    for (const line of lines) {
        if (excludeLine && line === excludeLine) continue;
        const lp = line.product_id;
        if (!lp) continue;
        if ((lp.id ?? lp) === (product.id ?? product)) total += line.qty ?? line.quantity ?? 0;
    }
    return total;
}

function checkStock(pos, product, requestedQty, excludeLine) {
    if (!pos?.config?.display_stock || !product || isService(product)) return null;
    const cfg = pos.config;
    const allowOutOfStock = cfg.allow_order_out_of_stock !== false;
    const stock = getStock(pos, product);
    if (stock === null) return null;
    const name = product.display_name || product.name || 'this product';
    const denyBelow = Number(cfg.deny_order_below_qty ?? 0);
    const order = pos.selectedOrder || pos.currentOrder;
    const inCart = getAlreadyInCart(pos, order, product, excludeLine);
    const totalAfter = inCart + (Number(requestedQty) || 0);
    if (!allowOutOfStock && stock <= 0)
        return { block: true, title: "Out of Stock", body: `"${name}" is out of stock.` };
    if (!allowOutOfStock && totalAfter > stock)
        return { block: true, title: "Insufficient Stock", body: `Cannot add "${name}". Available: ${stock}.` };
    if (denyBelow > 0 && stock <= denyBelow)
        return { block: true, title: "Stock Limit Reached", body: `"${name}" stock (${stock}) at or below minimum (${denyBelow}).` };
    if (denyBelow > 0 && (stock - totalAfter) <= denyBelow)
        return { block: true, title: "Stock Limit Reached", body: `"${name}" would leave ${stock - totalAfter} units, below minimum (${denyBelow}).` };
    return null;
}

patch(ProductScreen.prototype, {
    setup() {
        super.setup(...arguments);
        this.dialog = useService("dialog");
        window.__inomDialogService = this.dialog;
    },
    async addProductToOrder(product) {
        try {
            const warn = checkStock(this.pos, product, 1, null);
            if (warn?.block) { showWarning(this, warn.title, warn.body); return; }
        } catch (e) { console.warn("[Inom Stock] addProductToOrder error:", e.message); }
        return await super.addProductToOrder(...arguments);
    },
});

patch(PosStore.prototype, {
    async setup() {
        await super.setup(...arguments);
        try { this._inomPatchOrderLine(); } catch (e) {}
    },
    async addLineToCurrentOrder(vals, opts = {}, configure = true) {
        try {
            const product = vals?.product_id || vals?.product_tmpl_id;
            if (product) {
                const prod = typeof product === 'object' ? product
                    : this.models['product.product'].getAll().find(p => p.id === product)
                    || this.models['product.template'].getAll().find(p => p.id === product);
                if (prod) {
                    const warn = checkStock(this, prod, 1, null);
                    if (warn?.block) { showWarning(this, warn.title, warn.body); return; }
                }
            }
        } catch (e) { console.warn("[Inom Stock] addLineToCurrentOrder error:", e.message); }
        const result = await super.addLineToCurrentOrder(...arguments);
        try { this._inomPatchOrderLine(); } catch (e) {}
        return result;
    },
    _inomPatchOrderLine() {
        const all = this.models['pos.order.line'].getAll();
        if (!all?.length) return;
        const proto = Object.getPrototypeOf(all[0]);
        if (!proto || proto._inomPatched) return;
        const methodName = typeof proto.set_quantity === 'function' ? 'set_quantity'
            : typeof proto.setQuantity === 'function' ? 'setQuantity' : null;
        if (!methodName) return;
        const orig = proto[methodName];
        const posStore = this;
        proto[methodName] = function (quantity, keep_price) {
            try {
                const qty = parseFloat(quantity);
                if (!isNaN(qty) && qty > 0) {
                    const product = this.product_id || (typeof this.get_product === 'function' && this.get_product());
                    if (product) {
                        const warn = checkStock(posStore, product, qty, this);
                        if (warn?.block) { showWarning({ dialog: window.__inomDialogService }, warn.title, warn.body); return false; }
                    }
                }
            } catch (e) { console.warn("[Inom Stock] qty setter error:", e.message); }
            return orig.apply(this, arguments);
        };
        proto._inomPatched = true;
    },
});

patch(PaymentScreen.prototype, {
    setup() {
        super.setup(...arguments);
        this.dialog = useService("dialog");
        window.__inomDialogService = this.dialog;
    },
    async validateOrder(isForceValidate) {
        const pos = this.pos;
        if (pos.config?.display_stock) {
            const order = pos.selectedOrder || pos.currentOrder;
            for (const line of getOrderLines(pos, order)) {
                const product = line.product_id;
                if (!product || isService(product)) continue;
                const stock = getStock(pos, product);
                if (stock === null) continue;
                const qty = line.qty ?? line.quantity ?? 0;
                const name = product.display_name || product.name || 'this product';
                const denyBelow = Number(pos.config.deny_order_below_qty ?? 0);
                const allowOutOfStock = pos.config.allow_order_out_of_stock !== false;
                if (!allowOutOfStock && stock <= 0) { showWarning(this, "Cannot Validate Order", `"${name}" is out of stock.`); return; }
                if (!allowOutOfStock && qty > stock) { showWarning(this, "Cannot Validate Order", `"${name}" — ordered ${qty}, only ${stock} available.`); return; }
                if (denyBelow > 0 && (stock - qty) <= denyBelow) { showWarning(this, "Cannot Validate Order", `"${name}" — leaves ${stock - qty} units, below minimum (${denyBelow}).`); return; }
            }
        }

        const result = await super.validateOrder(...arguments);

        setTimeout(() => {
            try { pos._syncStock?.(); console.log("[Inom] Post-sale sync 1s"); }
            catch (e) { console.warn("[Inom] syncStock 1s failed:", e); }
        }, 1000);

        setTimeout(() => {
            try { pos._syncStock?.(); console.log("[Inom] Post-sale sync 5s"); }
            catch (e) { console.warn("[Inom] syncStock 5s failed:", e); }
        }, 5000);

        return result;
    },
});