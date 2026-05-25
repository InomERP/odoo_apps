/** @odoo-module **/
import { Component, useState } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { useService } from "@web/core/utils/hooks";

export class LowStockButton extends Component {
    static template = "inom_pos_stock_badge.LowStockButton";
    static props = {};

    setup() {
        this.pos = usePos();
        this.dialog = useService("dialog");
        this.state = useState({ show: false });
    }

    get lowStockProducts() {
        const threshold = this.pos.config.low_stock_threshold ?? 5;
        const records = this.pos.models['product.template']?.records;
        if (!records) return [];
        return [...records.values()].filter(p => {
            const qty = p.pos_qty ?? 0;
            return qty <= threshold;
        }).sort((a, b) => (a.pos_qty ?? 0) - (b.pos_qty ?? 0));
    }

    togglePopup() {
        this.state.show = !this.state.show;
    }
}
