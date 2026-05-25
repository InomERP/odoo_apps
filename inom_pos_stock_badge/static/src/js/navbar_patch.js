/** @odoo-module **/
import { Navbar } from "@point_of_sale/app/navbar/navbar";
import { LowStockButton } from "@inom_pos_stock_badge/js/low_stock_button";
import { patch } from "@web/core/utils/patch";

patch(Navbar, {
    components: {
        ...Navbar.components,
        LowStockButton,
    },
});
