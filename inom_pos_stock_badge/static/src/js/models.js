/** @odoo-module */

import { Order } from "@point_of_sale/app/store/models";
import { patch } from "@web/core/utils/patch";

patch(Order.prototype, {

    export_for_printing() {
        const result = super.export_for_printing(...arguments);

        const total_items = this.get_orderlines().reduce((sum, line) => {
            return sum + line.get_quantity();
        }, 0);

        result.total_items = total_items;

        return result;
    },

});