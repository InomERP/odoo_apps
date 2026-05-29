/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";

patch(TicketScreen.prototype, {
    get filteredOrderList() {
        try {
            const rule = this.pos?.accessRule;
            if (!rule?.restrict_salesperson_orders) {
                return super.filteredOrderList;
            }
            const uid = this.pos?.user?.id;
            const allOrders = super.filteredOrderList || [];
            return allOrders.filter((order) => {
                const orderEmpUserId = order.employee_id?.user_id?.id ?? order.employee_id?.user_id;
                const orderUserId = order.user_id?.id ?? order.user_id;
                return orderEmpUserId === uid || orderUserId === uid;
            });
        } catch (e) {
            console.warn("[inom] filteredOrderList patch failed:", e);
            return super.filteredOrderList;
        }
    },
});




















// /** @odoo-module **/

// import { patch } from "@web/core/utils/patch";
// import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";

// patch(TicketScreen.prototype, {
//     get filteredOrderList() {
//         try {
//             const rule = this.pos?.accessRule;
//             if (!rule?.restrict_salesperson_orders) {
//                 return super.filteredOrderList;
//             }
//             const uid = this.pos?.user?.id;
//             const allOrders = super.filteredOrderList || [];
//             return allOrders.filter((order) => {
//                 const orderUid = order.user_id?.id ?? order.user_id;
//                 return orderUid === uid;
//             });
//         } catch(e) {
//             console.warn("[inom] filteredOrderList patch failed:", e);
//             return super.filteredOrderList;
//         }
//     },
// });