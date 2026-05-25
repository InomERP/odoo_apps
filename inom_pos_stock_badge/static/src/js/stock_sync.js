/** @odoo-module **/
import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/store/pos_store";
import { reactive } from "@odoo/owl";

patch(PosStore.prototype, {
    async setup() {
        await super.setup(...arguments);
        this.stockMap = reactive({});
        this.stockVersion = reactive({ v: 0 });
        window._posInstance = this;
        await this._syncStock();
        setInterval(() => this._syncStock(), 30000);
    },

    async _syncStock() {
        try {
            const cfg = this.config;
            const allProducts = this.models['product.template'].getAll();
            if (!allProducts || !allProducts.length) return;

            const ids = allProducts.map(p => p.id).filter(Boolean);
            if (!ids.length) return;

            let locationId = false;
            if (cfg.show_stock_of === 'current_session' && cfg.stock_location_id) {
                const loc = cfg.stock_location_id;
                if (loc && typeof loc === 'object') {
                    const rawId = loc.rawId ?? loc._raw?.id ?? loc.id;
                    if (typeof rawId === 'number' && rawId > 0) {
                        locationId = rawId;
                    } else {
                        const parsed = parseInt(String(rawId));
                        if (!isNaN(parsed) && parsed > 0) locationId = parsed;
                    }
                } else if (typeof loc === 'number') {
                    locationId = loc;
                } else if (Array.isArray(loc)) {
                    locationId = loc[0];
                }
            }

            console.log(`[Inom] Syncing stock for ${ids.length} products, location: ${locationId || 'all'}, stock_type: ${cfg.stock_type}`);

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

            if (!result || !result.length) {
                console.warn("[Inom] Empty result from server");
                return;
            }

            const newMap = {};
            for (const { id, pos_qty, virtual_available } of result) {
                newMap[id] = {
                    pos_qty: typeof pos_qty === 'number' ? pos_qty : 0,
                    virtual_available: typeof virtual_available === 'number' ? virtual_available : 0,
                };
            }

            for (const key of Object.keys(this.stockMap)) {
                if (!(key in newMap)) delete this.stockMap[key];
            }
            for (const [key, val] of Object.entries(newMap)) {
                this.stockMap[key] = val;
            }

            this.stockVersion.v += 1;
            window._debugStockMap = this.stockMap;
            console.log(`[Inom] ✅ Stock synced v${this.stockVersion.v}, products: ${result.length}`);

            const sample = Object.entries(newMap).slice(0, 3);
            sample.forEach(([id, d]) => console.log(`  tmpl ${id}: pos_qty=${d.pos_qty}, virtual=${d.virtual_available}`));

        } catch (e) {
            console.error("[Inom] ❌ Stock sync error:", e);
        }
    }
});