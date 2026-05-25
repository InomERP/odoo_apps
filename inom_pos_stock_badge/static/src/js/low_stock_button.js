/** @odoo-module **/
import { Component, useState } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/store/pos_hook";
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
        const threshold = this.pos.config.product_low_stock ?? 5;
        const stockType = this.pos.config?.stock_type || "on_hand";
        const stockMap = this.pos.stockMap || {};
        const products = this.pos.db?.product_by_id || {};

        return Object.values(products)
            .map(p => {
                const tmplId = p.product_tmpl_id;
                const stockData = stockMap[tmplId] || stockMap[String(tmplId)] || null;
                const qty = stockData
                    ? (stockType === "available"
                        ? Number(stockData.virtual_available ?? 0)
                        : Number(stockData.pos_qty ?? 0))
                    : 0;
                return { ...p, _qty: qty };
            })
            .filter(p => p._qty < threshold)
            .sort((a, b) => a._qty - b._qty);
    }

    togglePopup() {
        this.state.show = !this.state.show;
    }
}