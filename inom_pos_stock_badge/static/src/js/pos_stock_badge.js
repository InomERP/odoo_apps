/** @odoo-module **/
import { ProductCard } from "@point_of_sale/app/components/product_card/product_card";
import { patch } from "@web/core/utils/patch";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { useState, useEffect, reactive } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

const BADGE_STATE = {
    NORMAL: "normal",
    LOW: "low",
    OUT: "out",
};
const BADGE_COLORS = {
    [BADGE_STATE.OUT]: { bg: "#DC3545", fg: "#FFFFFF" },
    [BADGE_STATE.LOW]: { bg: "#FD7E14", fg: "#FFFFFF" },
};

patch(ProductCard.prototype, {
    setup() {
        super.setup(...arguments);
        this.pos = usePos();
        this.orm = useService("orm");
        this.locationState = useState({ show: false, data: [], loading: false });
        this.stockState = useState({ qty: 0, version: 0 });
        useEffect(
            () => {
                const product = this.props.product;
                if (!product) return;
                const tmplId = Array.isArray(product.product_tmpl_id)
                    ? product.product_tmpl_id[0]
                    : (product.product_tmpl_id || product.id);
                const stockData = this.pos.stockMap?.[tmplId];
                const cfg = this.pos.config;
                const stockType = cfg?.stock_type || 'on_hand';
                let qty = 0;
                if (stockType === 'available') {
                    qty = stockData?.virtual_available ?? product.virtual_available ?? 0;
                } else {
                    qty = stockData?.pos_qty ?? product.pos_qty ?? product.qty_available ?? 0;
                }
                this.stockState.qty = typeof qty === 'number' ? qty : 0;
                this.stockState.version = this.pos.stockVersion?.v || 0;
            },
            () => [this.pos.stockVersion?.v, this.pos.stockMap]
        );
    },

    get _StockQty() {
        return this.stockState.qty;
    },

    get stockBadgeConfig() {
        try {
            const cfg = this.pos.config;
            return {
                enabled: cfg.display_stock || false,
                position: cfg.badge_position || "top_left",
                bgColor: cfg.badge_bg_color || "#28A745",
                fgColor: cfg.badge_font_color || "#FFFFFF",
                lowThreshold: cfg.low_stock_threshold ?? 5.0,
                stockType: cfg.stock_type || "on_hand",
                allowOutOfStock: cfg.allow_order_out_of_stock !== undefined
                    ? cfg.allow_order_out_of_stock
                    : true,
                showStockOf: cfg.show_stock_of || "all_warehouse",
                locationId: cfg.stock_location_id || false,
            };
        } catch (e) {
            return {
                enabled: false,
                position: "top_left",
                bgColor: "#28A745",
                fgColor: "#FFFFFF",
                lowThreshold: 5.0,
                stockType: "on_hand",
                showStockOf: "all_warehouse",
                locationId: false,
            };
        }
    },

    get stockBadgeClass() {
        return `inom-badge-state-${this._BadgeState}`;
    },

    get stockBadgeStyle() {
        try {
            const state = this._BadgeState;
            if (state === BADGE_STATE.NORMAL) {
                return {
                    bg: this.stockBadgeConfig.bgColor || "#28A745",
                    fg: this.stockBadgeConfig.fgColor || "#FFFFFF",
                };
            }
            return BADGE_COLORS[state] || { bg: "#28A745", fg: "#FFFFFF" };
        } catch (e) {
            return { bg: "#28A745", fg: "#FFFFFF" };
        }
    },

    get _BadgeState() {
        const qty = this._StockQty;
        const threshold = this.stockBadgeConfig.lowThreshold;
        if (qty <= 0)         return BADGE_STATE.OUT;
        if (qty <= threshold) return BADGE_STATE.LOW;
        return BADGE_STATE.NORMAL;
    },

    get stockQtyDisplay() {
        const qty = this._StockQty;
        return Number.isInteger(qty) ? String(qty) : qty.toFixed(1);
    },

    async onClickBadge(ev) {
        ev.stopPropagation();
        this.locationState.show = !this.locationState.show;
        if (this.locationState.show && this.locationState.data.length === 0) {
            this.locationState.loading = true;
            try {
                const session = [...this.pos.models['pos.session'].records.values()][0];
                const result = await this.orm.call(
                    'pos.session',
                    'get_stock_by_location',
                    [session.id, [this.props.product.id]],
                );
                this.locationState.data = result[this.props.product.id] || [];
            } catch (e) {
                console.warn("Location stock error:", e.message);
            } finally {
                this.locationState.loading = false;
            }
        }
    },
});
