/** @odoo-module **/
import { patch } from "@web/core/utils/patch";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { OrderReceipt } from "@point_of_sale/app/screens/receipt_screen/receipt/order_receipt";
import { onMounted, onPatched } from "@odoo/owl";

function getTotalItems(order) {
    if (!order) return 0;
    const lines = order.lines || [];
    const arr = Array.isArray(lines) ? lines : [...lines];
    if (!arr.length) return 0;
    const total = arr.reduce((sum, line) => {
        const qty = line.qty ?? line.get_quantity?.() ?? 0;
        return sum + qty;
    }, 0);
    return Number.isInteger(total) ? total : parseFloat(total.toFixed(2));
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