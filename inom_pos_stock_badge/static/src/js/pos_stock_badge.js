/** @odoo-module **/
import { ProductCard } from "@point_of_sale/app/components/product_card/product_card";
import { patch } from "@web/core/utils/patch";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { proxy } from "@odoo/owl";
import { getStockQty, getTemplateId } from "@inom_pos_stock_badge/js/stock_utils";

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
        this.locationState = proxy({ show: false, data: [], loading: false });
    },

    /** Stock qty of the card's product, or null when it has no badge. */
    get stockQty() {
        if (!this.pos.config.display_stock) {
            return null;
        }
        return getStockQty(this.pos, this.props.product);
    },

    get showStockBadge() {
        return this.stockQty !== null;
    },

    get stockBadgeState() {
        const qty = this.stockQty;
        if (qty <= 0) {
            return BADGE_STATE.OUT;
        }
        if (qty <= (this.pos.config.low_stock_threshold ?? 5)) {
            return BADGE_STATE.LOW;
        }
        return BADGE_STATE.NORMAL;
    },

    get stockBadgeClass() {
        const position = this.pos.config.badge_position || "top_left";
        return `inom-stock-badge inom-badge-${position} inom-badge-state-${this.stockBadgeState}`;
    },

    get stockBadgeStyle() {
        const state = this.stockBadgeState;
        const colors =
            state === BADGE_STATE.NORMAL
                ? {
                      bg: this.pos.config.badge_bg_color || "#28A745",
                      fg: this.pos.config.badge_font_color || "#FFFFFF",
                  }
                : BADGE_COLORS[state];
        return `background-color:${colors.bg};color:${colors.fg};`;
    },

    get stockQtyDisplay() {
        const qty = this.stockQty;
        return Number.isInteger(qty) ? String(qty) : qty.toFixed(1);
    },

    get locationPopupClass() {
        const position = this.pos.config.badge_position || "top_left";
        return `inom-location-popup inom-location-popup-${position}`;
    },

    async onClickBadge() {
        this.locationState.show = !this.locationState.show;
        if (!this.locationState.show) {
            return;
        }
        this.locationState.loading = true;
        try {
            const tmplId = getTemplateId(this.props.product);
            const result = await this.pos.data.silentCall("pos.session", "get_stock_by_location", [
                this.pos.session.id,
                [tmplId],
            ]);
            this.locationState.data = (result && result[tmplId]) || [];
        } finally {
            this.locationState.loading = false;
        }
    },
});
