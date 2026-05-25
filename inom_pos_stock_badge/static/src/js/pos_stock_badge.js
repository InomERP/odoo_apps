/** @odoo-module **/
import { ProductCard } from "@point_of_sale/app/generic_components/product_card/product_card";
import { patch } from "@web/core/utils/patch";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { useState, useEffect } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

const BADGE_STATE = { NORMAL: "normal", LOW: "low", OUT: "out" };
const BADGE_COLORS = {
    out: { bg: "#DC3545", fg: "#FFFFFF" },
    low: { bg: "#FD7E14", fg: "#FFFFFF" },
};

patch(ProductCard.prototype, {
    setup() {
        super.setup(...arguments);

        const pos = usePos();
        this.pos = pos;
        this.orm = useService("orm");
        this.locationState = useState({ show: false, data: [], loading: false });
        this.stockState = useState({ qty: 0, version: -1 });

        useEffect(
            (currentVersion) => {
                const product = this.props.product;
                if (!product) return;

                // ✅ FIX: template ID safely nikalo
                const tmplId = product.product_tmpl_id?.id
                    || product.product_tmpl_id
                    || product.id;

                const stockData = pos.stockMap?.[tmplId]
                    || pos.stockMap?.[String(tmplId)];

                const cfg = pos.config;
                const stockType = cfg?.stock_type || 'on_hand';

                let qty = 0;
                if (stockData) {
                    qty = stockType === 'available'
                        ? (stockData.virtual_available ?? 0)
                        : (stockData.pos_qty ?? 0);
                } else {
                    qty = stockType === 'available'
                        ? (product.virtual_available ?? 0)
                        : (product.qty_available ?? product.pos_qty ?? 0);
                }

                this.stockState.qty = typeof qty === 'number' ? qty : 0;
                this.stockState.version = currentVersion;
            },
            () => [pos.stockVersion?.v ?? 0]
        );
    },

    get _StockQty() {
        return this.stockState.qty;
    },

    // ✅ ADD: XML mein stockBadgeClass use ho raha tha — yeh missing tha
    get stockBadgeClass() {
        const state = this._BadgeState;
        if (state === "out") return "inom-out-of-stock";
        if (state === "low") return "inom-low-stock";
        return "inom-in-stock";
    },

    get stockBadgeConfig() {
        const cfg = this.pos.config;
        return {
            enabled: cfg?.display_stock || false,
            position: cfg?.badge_position || "top_left",
            bgColor: cfg?.badge_bg_color || "#28A745",
            fgColor: cfg?.badge_font_color || "#FFFFFF",
            lowThreshold: cfg?.low_stock_threshold ?? 5.0,
            stockType: cfg?.stock_type || "on_hand",
            allowOutOfStock: cfg?.allow_order_out_of_stock ?? true,
            showStockOf: cfg?.show_stock_of || "all_warehouse",
        };
    },

    get _BadgeState() {
        const qty = this._StockQty;
        const threshold = this.stockBadgeConfig.lowThreshold;
        if (qty <= 0)         return BADGE_STATE.OUT;
        if (qty <= threshold) return BADGE_STATE.LOW;
        return BADGE_STATE.NORMAL;
    },

    get stockBadgeStyle() {
        const state = this._BadgeState;
        if (state === BADGE_STATE.NORMAL) {
            return { bg: this.stockBadgeConfig.bgColor, fg: this.stockBadgeConfig.fgColor };
        }
        return BADGE_COLORS[state] || { bg: "#28A745", fg: "#FFFFFF" };
    },

    get stockQtyDisplay() {
        const qty = this._StockQty;
        return Number.isInteger(qty) ? String(qty) : qty.toFixed(1);
    },

    async onClickBadge(ev) {
        ev.stopPropagation();
        this.locationState.show = !this.locationState.show;
        if (this.locationState.show && !this.locationState.data.length) {
            this.locationState.loading = true;
            try {
                const session = this.pos.models['pos.session'].getAll()[0];
                const result = await this.orm.call(
                    'pos.session', 'get_stock_by_location',
                    [session.id, [this.props.product.id]]
                );
                this.locationState.data = result[this.props.product.id] || [];
            } catch (e) {
                console.warn("Location stock error:", e);
            } finally {
                this.locationState.loading = false;
            }
        }
    },
});