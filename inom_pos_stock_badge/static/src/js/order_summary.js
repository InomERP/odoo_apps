/** @odoo-module **/
import { patch } from "@web/core/utils/patch";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { OrderReceipt } from "@point_of_sale/app/screens/receipt_screen/receipt/order_receipt";
import { onMounted, onPatched } from "@odoo/owl";

function getTotalItems(order) {
    if (!order) {
        return 0;
    }

    // Get all POS order lines
    const lines = order.get_orderlines ? order.get_orderlines() : [];

    if (!lines.length) {
        return 0;
    }

    // Sum all quantities
    const total = lines.reduce((sum, line) => {
        return sum + (line.get_quantity ? line.get_quantity() : 0);
    }, 0);

    return parseFloat(total.toFixed(2));
}

function updatePosTotal(order) {
    try {
        const totalEl = document.querySelector('.total');
        if (!totalEl) return;
        let div = document.querySelector('.inom-total-items');
        if (!div) {
            div = document.createElement('div');
            div.className = 'inom-total-items';
            div.style.cssText = 'color:#00A09D;font-weight:bold;font-size:14px;padding:4px 8px;';
            totalEl.before(div);
        }
        div.textContent = `Total Number Of Items: ${getTotalItems(order)}`;
    } catch (e) {}
}

patch(ProductScreen.prototype, {
    setup() {
        super.setup(...arguments);
        onMounted(() => updatePosTotal(this.pos?.selectedOrder));
        onPatched(() => updatePosTotal(this.pos?.selectedOrder));
    },
});

patch(OrderReceipt.prototype, {
    get totalItemCount() {
        const order = this.props?.order;
        return getTotalItems(order);
    },
});