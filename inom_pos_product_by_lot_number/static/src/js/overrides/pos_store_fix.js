/** @odoo-module **/
import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/store/pos_store";

/**
 * PosStore config defaults — Odoo 19 compatible.
 * Sets iml_* config defaults after processServerData.
 */
patch(PosStore.prototype, {

    async setup(env, deps) {
        await super.setup(env, deps);

        const cfg = this.config;
        if (cfg) {
            if (cfg.iml_enable_lot_popup === undefined || cfg.iml_enable_lot_popup === null)
                cfg.iml_enable_lot_popup = true;
            if (cfg.iml_strict_qty_validation === undefined || cfg.iml_strict_qty_validation === null)
                cfg.iml_strict_qty_validation = true;
            if (cfg.iml_print_lot_on_receipt === undefined || cfg.iml_print_lot_on_receipt === null)
                cfg.iml_print_lot_on_receipt = true;
            if (cfg.iml_check_duplicate_serial === undefined || cfg.iml_check_duplicate_serial === null)
                cfg.iml_check_duplicate_serial = true;
            if (cfg.iml_allow_create_lot === undefined || cfg.iml_allow_create_lot === null)
                cfg.iml_allow_create_lot = false;
            if (!cfg.iml_lot_autocomplete_min_chars)
                cfg.iml_lot_autocomplete_min_chars = 2;
            if (!cfg.iml_lot_autocomplete_limit)
                cfg.iml_lot_autocomplete_limit = 20;
        }
    },
});
