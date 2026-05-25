/** @odoo-module **/

import { ProductCard } from "@point_of_sale/app/generic_components/product_card/product_card";
import { patch } from "@web/core/utils/patch";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { useState, onMounted, onWillUnmount } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

const BADGE_STATE = {
    NORMAL: "normal",
    LOW: "low",
    OUT: "out",
};

const BADGE_COLORS = {
    out: { bg: "#DC3545", fg: "#FFFFFF" },
    low: { bg: "#FD7E14", fg: "#FFFFFF" },
};

const _inomBadgeRegistry = new Set();

window._inomBadgeRegistry = _inomBadgeRegistry;

// Called by _syncStock after stockMap is updated
window._inomNotifyBadges = function() {
    let count = 0;
    for (const badge of _inomBadgeRegistry) {
        try {
            badge._inomSv.v += 1;
            count++;
        } catch(e) {}
    }
    console.log("[Inom] Notified", count, "badge components");
};

patch(ProductCard.prototype, {
    setup() {
        super.setup(...arguments);

        this.pos = usePos();
        this.orm = useService("orm");

        this.locationState = useState({
            show: false,
            data: [],
            loading: false,
        });

        this._inomSv = useState({ v: 0 });

        onMounted(() => {
            _inomBadgeRegistry.add(this);
        });

        onWillUnmount(() => {
            _inomBadgeRegistry.delete(this);
        });
    },

    _computeStockQty() {
        try {
            const productId = this.props.productId;
            if (!productId) return 0;

            const product = this.pos.db.get_product_by_id(productId);
            if (!product) return 0;

            const tmplId = product.product_tmpl_id;
            if (!tmplId) return 0;

            const stockMap = this.pos.stockMap;
            if (!stockMap) return 0;

            const stockData = stockMap[tmplId] || stockMap[String(tmplId)] || null;
            if (!stockData) return 0;

            const stockType = this.pos.config?.stock_type || "on_hand";
            return stockType === "available"
                ? Number(stockData.virtual_available ?? 0)
                : Number(stockData.pos_qty ?? 0);
        } catch (e) {
            return 0;
        }
    },

    get _StockQty() {

        const _track = this._inomSv.v;
        return this._computeStockQty();
    },

    get stockBadgeConfig() {
        const cfg = this.pos.config;
        return {
            enabled: cfg?.display_stock || false,
            position: cfg?.badge_position || "top_left",
            bgColor: cfg?.badge_bg_color || "#28A745",
            fgColor: cfg?.badge_font_color || "#FFFFFF",
            lowThreshold: cfg?.low_stock_threshold ?? 5,
            stockType: cfg?.stock_type || "on_hand",
            allowOutOfStock: cfg?.allow_order_out_of_stock ?? true,
            showStockOf: cfg?.show_stock_of || "all_warehouse",
        };
    },

    get _BadgeState() {
        const qty = this._StockQty;
        const threshold = this.stockBadgeConfig.lowThreshold;
        if (qty <= 0) return BADGE_STATE.OUT;
        if (qty <= threshold) return BADGE_STATE.LOW;
        return BADGE_STATE.NORMAL;
    },

    get stockBadgeClass() {
        const state = this._BadgeState;
        const position = this.stockBadgeConfig.position || "top_right";
        const stateClass = state === BADGE_STATE.OUT ? "inom-out-of-stock" :
                           state === BADGE_STATE.LOW ? "inom-low-stock" :
                           "inom-in-stock";
        return `${stateClass} inom-badge-${position}`;
    },

    get stockBadgeStyle() {
        const state = this._BadgeState;
        if (state === BADGE_STATE.OUT) return BADGE_COLORS.out;
        if (state === BADGE_STATE.LOW) return BADGE_COLORS.low;
        return {
            bg: this.stockBadgeConfig.bgColor || "#28A745",
            fg: this.stockBadgeConfig.fgColor || "#FFFFFF",
        };
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
                const product = this.pos.db.get_product_by_id(this.props.productId);
                const tmplId = product?.product_tmpl_id;
                if (tmplId) {
                    const result = await this.orm.call(
                        "pos.session",
                        "get_stock_by_location",
                        [this.pos.pos_session_id, [tmplId]],
                    );
                    this.locationState.data = result[tmplId] || [];
                }
            } catch (e) {
                console.warn("Location stock error:", e.message);
            } finally {
                this.locationState.loading = false;
            }
        }
    },
});