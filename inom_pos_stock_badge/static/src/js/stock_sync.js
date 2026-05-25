/** @odoo-module **/

import { PosStore } from "@point_of_sale/app/store/pos_store";
import { patch } from "@web/core/utils/patch";

patch(PosStore.prototype, {

    async _processData(loadedData) {
        await super._processData(...arguments);

        // Plain objects — we use a custom event to force badge re-renders
        this.stockVersion = { v: 0 };
        this.stockMap = {};

        const products = loadedData["product.product"] || [];
        console.log("[Inom] _processData: product.product =", products.length);

        const source = products.length
            ? products
            : Object.values(this.db?.product_by_id || {});

        for (const product of source) {
            const tmplId = Array.isArray(product.product_tmpl_id)
                ? product.product_tmpl_id[0]
                : (product.product_tmpl_id?.id || product.product_tmpl_id);
            if (!tmplId) continue;

            const entry = {
                pos_qty: Number(product.inom_stock_qty ?? product.qty_available ?? 0),
                virtual_available: Number(product.inom_virtual_qty ?? product.virtual_available ?? 0),
            };
            this.stockMap[tmplId] = entry;
            this.stockMap[String(tmplId)] = entry;
        }

        this.stockVersion.v = Date.now();
        window._inomStockVersion = this.stockVersion.v;
        window._debugStockMap = this.stockMap;
        console.log("✅ Inom stockMap ready =>", Object.keys(this.stockMap).length / 2, "products");
    },
});