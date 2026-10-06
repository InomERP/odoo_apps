/** @odoo-module **/
import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/services/pos_store";
import { getTemplateId } from "@inom_pos_stock_badge/js/stock_utils";

const STOCK_SYNC_INTERVAL = 30000;

patch(PosStore.prototype, {
    async setup() {
        await super.setup(...arguments);
        // {product.template id: qty}; replaced as a whole on each sync so it stays reactive.
        this.stockMap = {};
        if (this.config.display_stock) {
            this.syncStock();
            setInterval(() => this.syncStock(), STOCK_SYNC_INTERVAL);
        }
    },

    async syncStock() {
        if (this._inomStockSyncing) {
            // A sync is in flight with possibly outdated data: run again once it is done.
            this._inomStockSyncPending = true;
            return;
        }
        this._inomStockSyncing = true;
        try {
            const ids = this.models["product.template"].getAllIds();
            if (!ids.length) {
                return;
            }
            const result = await this.data.silentCall("pos.config", "get_inom_pos_stock", [
                this.config.id,
                ids,
            ]);
            if (result && !this._inomStockSyncPending) {
                this.stockMap = result;
            }
        } catch (e) {
            console.warn("[Inom POS Stock] stock sync failed:", e);
        } finally {
            this._inomStockSyncing = false;
        }
        if (this._inomStockSyncPending) {
            this._inomStockSyncPending = false;
            await this.syncStock();
        }
    },

    async validateOrder(args = {}) {
        const order = args.order || this.getOrder();
        const soldByTemplate = {};
        for (const line of order?.lines || []) {
            const tmplId = getTemplateId(line.product_id);
            if (tmplId in this.stockMap) {
                soldByTemplate[tmplId] = (soldByTemplate[tmplId] || 0) + line.qty;
            }
        }
        const result = await super.validateOrder(...arguments);
        if (result && this.config.display_stock) {
            // Update badges right away, then confirm with the server (order is synced by now).
            const stockMap = { ...this.stockMap };
            for (const [tmplId, qty] of Object.entries(soldByTemplate)) {
                stockMap[tmplId] -= qty;
            }
            this.stockMap = stockMap;
            this.syncStock();
        }
        return result;
    },
});
