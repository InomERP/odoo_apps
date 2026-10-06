/** @odoo-module **/
/**
 * Stock guards configured in POS settings ("Allow POS Order When Product is Out of
 * Stock" and "Deny POS Order When Product Qty goes down to"), enforced when a product
 * is added, when a line quantity is changed, and again when the order is validated.
 */
import { patch } from "@web/core/utils/patch";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { PosStore } from "@point_of_sale/app/services/pos_store";
import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import OrderPaymentValidation from "@point_of_sale/app/utils/order_payment_validation";
import { checkStock, getTemplateId } from "@inom_pos_stock_badge/js/stock_utils";

// Order lines have no direct access to the POS store; keep a reference for the qty guard.
let posStore = null;
// Set while core merges a freshly added line into an existing one: the add was
// already checked in addLineToOrder and the temporary line would be counted twice.
let skipQtyGuard = false;

patch(PosStore.prototype, {
    async setup() {
        posStore = this;
        return await super.setup(...arguments);
    },

    async canAddProductToCurrentOrder(product) {
        if (!(await super.canAddProductToCurrentOrder(...arguments))) {
            return false;
        }
        const order = this.getOrder();
        const warning = !order?.preset_id?.is_return && checkStock(this, product, 1, { order });
        if (warning) {
            this.dialog.add(AlertDialog, warning);
            return false;
        }
        return true;
    },

    async addLineToOrder(vals, order, opts = {}, configure = true) {
        let product = vals?.product_id || vals?.product_tmpl_id;
        if (typeof vals?.product_id === "number") {
            product = this.models["product.product"].get(vals.product_id);
        } else if (typeof product === "number") {
            product = this.models["product.template"].get(product);
        }
        if (product && !order?.preset_id?.is_return) {
            const qty = "qty" in vals ? Number(vals.qty) : 1;
            const warning = checkStock(this, product, qty, { order });
            if (warning) {
                this.dialog.add(AlertDialog, warning);
                return;
            }
        }
        return await super.addLineToOrder(...arguments);
    },
});

patch(PosOrderline.prototype, {
    setQuantity(quantity, keep_price) {
        const newQty = typeof quantity === "number" ? quantity : parseFloat("" + (quantity || 0));
        // Only guard increases; decreases, removals and refunds are always allowed.
        if (
            !skipQtyGuard &&
            newQty > 0 &&
            newQty > (this.qty || 0) &&
            !this.combo_parent_id &&
            !this.order_id?.preset_id?.is_return
        ) {
            const warning = checkStock(posStore, this.product_id, newQty, {
                order: this.order_id,
                excludeLine: this,
            });
            if (warning) {
                // Same contract as the core refund checks: callers display the
                // returned { title, body } and the quantity is left unchanged.
                return warning;
            }
        }
        return super.setQuantity(...arguments);
    },

    merge(orderline) {
        skipQtyGuard = true;
        try {
            return super.merge(...arguments);
        } finally {
            skipQtyGuard = false;
        }
    },
});

patch(OrderPaymentValidation.prototype, {
    async askBeforeValidation() {
        if ((await super.askBeforeValidation(...arguments)) === false) {
            return false;
        }
        const qtyByTemplate = new Map();
        for (const line of this.order?.lines || []) {
            if (line.qty > 0 && line.product_id) {
                const tmplId = getTemplateId(line.product_id);
                const entry = qtyByTemplate.get(tmplId) || { product: line.product_id, qty: 0 };
                entry.qty += line.qty;
                qtyByTemplate.set(tmplId, entry);
            }
        }
        for (const { product, qty } of qtyByTemplate.values()) {
            const warning = checkStock(this.pos, product, qty);
            if (warning) {
                this.pos.dialog.add(AlertDialog, {
                    title: warning.title,
                    body: warning.body,
                });
                return false;
            }
        }
        return true;
    },
});
