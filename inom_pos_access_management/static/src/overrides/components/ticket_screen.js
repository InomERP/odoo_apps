/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";

patch(TicketScreen.prototype, {
    getFilteredOrderList() {
        try {
            const orders = super.getFilteredOrderList(...arguments);
            const rule = this.pos?.accessRule;

            if (!rule?.restrict_salesperson_orders) {
                return orders;
            }

            const uid = this.pos?.user?.id;
            return orders.filter((order) => {
                const orderEmployeeUserId =
                    order.employee_id?.user_id?.id ?? order.employee_id?.user_id;
                const orderUserId = order.user_id?.id ?? order.user_id;
                return orderEmployeeUserId === uid || orderUserId === uid;
            });
        } catch (e) {
            console.warn("[inom] filtered order list patch failed:", e);
            return super.getFilteredOrderList(...arguments);
        }
    },

    get showSubPads() {
        // The sub-pads (numpad + Refund button) are only used to refund.
        if (this.pos.accessRule.hide_refund_button) {
            return false;
        }
        return super.showSubPads;
    },
});
