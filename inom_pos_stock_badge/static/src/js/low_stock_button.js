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
        const threshold = this.pos.config.low_stock_threshold ?? 5;
        const stockType = this.pos.config.stock_type || 'on_hand';


        const _v = this.pos.stockVersion?.v;

        const allTemplates = this.pos.models['product.template'].getAll();
        const allProducts = this.pos.models['product.product'].getAll();
        if (!allTemplates || !allTemplates.length) return [];

        return allTemplates
            .map(tmpl => {

                const stockData = this.pos.stockMap?.[tmpl.id]
                    || this.pos.stockMap?.[String(tmpl.id)];

                let qty = 0;
                if (stockData) {
                    qty = stockType === 'available'
                        ? (stockData.virtual_available ?? 0)
                        : (stockData.pos_qty ?? 0);
                } else {
                    qty = stockType === 'available'
                        ? (tmpl.virtual_available ?? 0)
                        : (tmpl.pos_qty ?? 0);
                }

                const variant = allProducts.find(p => p.product_tmpl_id?.id === tmpl.id);
                const name = variant?.display_name || variant?.name || tmpl.name || `Product #${tmpl.id}`;
                return { id: tmpl.id, name, pos_qty: qty };
            })
            .filter(p => p.pos_qty <= threshold)
            .sort((a, b) => a.pos_qty - b.pos_qty);
    }

    togglePopup() {
        this.state.show = !this.state.show;
    }
}