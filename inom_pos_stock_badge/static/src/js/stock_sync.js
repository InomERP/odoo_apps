/** @odoo-module **/
import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/services/pos_store";
import { reactive } from "@odoo/owl";

patch(PosStore.prototype, {
    async setup() {
        await super.setup(...arguments);
        this.stockMap = reactive({});
        this.stockVersion = reactive({ v: 0 });
        await this._syncStock();
        setInterval(() => this._syncStock(), 30000);

        this._lastLocationId = this._getCurrentLocationId();
        this._lastShowStockOf = this.config?.show_stock_of || 'all_warehouse';
        this._lastStockType = this.config?.stock_type || 'on_hand';
        setInterval(() => this._checkConfigChange(), 1000);
    },

    _getCurrentLocationId() {
        const cfg = this.config;
        if (!cfg) return false;
        const showStockOf = cfg.show_stock_of || 'all_warehouse';
        if (showStockOf === 'current_session' && cfg.stock_location_id) {
            return Array.isArray(cfg.stock_location_id)
                ? cfg.stock_location_id[0]
                : cfg.stock_location_id;
        }
        return false;
    },

    _checkConfigChange() {
        const newLocationId = this._getCurrentLocationId();
        const newShowStockOf = this.config?.show_stock_of || 'all_warehouse';
        const newStockType = this.config?.stock_type || 'on_hand';

        if (
            newLocationId !== this._lastLocationId ||
            newShowStockOf !== this._lastShowStockOf ||
            newStockType !== this._lastStockType
        ) {
            this._lastLocationId = newLocationId;
            this._lastShowStockOf = newShowStockOf;
            this._lastStockType = newStockType;
            this._syncStock();
        }
    },

    async _syncStock() {
        try {
            const records = this.models['product.template']?.records;
            if (!records) return;

            const ids = [...records.values()].map(p => p.id).filter(Boolean);
            if (!ids.length) return;

            const cfg = this.config;
            const showStockOf = cfg.show_stock_of || 'all_warehouse';

            const locationId = (showStockOf === 'current_session' && cfg.stock_location_id)
                ? (Array.isArray(cfg.stock_location_id)
                    ? cfg.stock_location_id[0]
                    : cfg.stock_location_id)
                : false;

            const result = await this.env.services.orm.call(
                'product.template',
                'get_pos_stock_by_location',
                [],
                {
                    product_ids: ids,
                    location_id: locationId,
                    stock_type: cfg.stock_type || 'on_hand',
                }
            );

            const newMap = {};
            result.forEach(({ id, pos_qty, virtual_available }) => {
                newMap[id] = {
                    pos_qty: typeof pos_qty === 'number' ? pos_qty : 0,
                    virtual_available: typeof virtual_available === 'number' ? virtual_available : 0,
                };
            });

            for (const key of Object.keys(this.stockMap)) {
                if (!(key in newMap)) delete this.stockMap[key];
            }
            Object.assign(this.stockMap, newMap);
            this.stockVersion.v += 1;
            window._debugStockMap = this.stockMap;
            console.log("✅ Stock synced v" + this.stockVersion.v + " (location=" + locationId + "):", newMap);

        } catch (e) {
            console.warn("Stock sync error:", e.message);
        }
    }
});