/** @odoo-module **/
import { Component, proxy } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { getStockQty } from "@inom_pos_stock_badge/js/stock_utils";

export class LowStockButton extends Component {
    static template = "inom_pos_stock_badge.LowStockButton";

    setup() {
        this.pos = usePos();
        this.state = proxy({ show: false });
    }

    get lowStockProducts() {
        const threshold = this.pos.config.low_stock_threshold ?? 5;
        const products = [];
        for (const product of this.pos.models["product.template"].getAll()) {
            const qty = getStockQty(this.pos, product);
            if (qty !== null && qty <= threshold) {
                products.push({ id: product.id, name: product.display_name, qty });
            }
        }
        return products.sort((a, b) => a.qty - b.qty);
    }

    togglePopup() {
        this.state.show = !this.state.show;
    }
}
