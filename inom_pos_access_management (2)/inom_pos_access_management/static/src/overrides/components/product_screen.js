/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";

patch(ProductScreen.prototype, {
    getNumpadButtons() {
        const buttons = super.getNumpadButtons(...arguments);
        const rule = this.pos.accessRule;
        if (!rule.disable_qty_button) {
            return buttons;
        }
        return buttons.map((button) =>
            button.value === "quantity" ? { ...button, disabled: true } : button
        );
    },
});
