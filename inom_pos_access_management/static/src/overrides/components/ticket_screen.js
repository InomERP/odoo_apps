/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
// Same module path in Odoo 17 and Odoo 18.
import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";

/**
 * Salesperson restriction on the POS Ticket Screen.
 *
 * Odoo-17 migration notes
 * -----------------------
 * The Ticket Screen's "give me the orders to show" entry point has
 * been refactored multiple times across Odoo 17 sub-versions:
 *
 *   • Early 17.0      → `getFilteredOrderList()`  (regular method)
 *   • Late 17.0 / 18  → `get filteredOrderList()` (getter on prototype)
 *
 * Rather than guess and risk silently no-op'ing on one of them, we
 * patch BOTH names. Each patch:
 *   1. checks whether the corresponding parent member actually exists
 *      (guarded `super` lookup — calling `undefined(...)` would throw);
 *   2. delegates to that parent to obtain the unfiltered base list;
 *   3. runs it through `_inomFilterOrders()` for the actual filtering.
 *
 * If a given form doesn't exist on the parent, the corresponding
 * override is simply never hit — harmless.
 *
 * Authoritative server-side enforcement (so the cashier truly cannot
 * see other staff's orders, even via a custom RPC) lives in
 * `models/pos_order.py::search_paid_order_ids`.  This JS layer only
 * adds an extra UI-side polish.
 */
patch(TicketScreen.prototype, {

    /**
     * Apply the salesperson-orders restriction to an order list.
     * Pure function — same input always produces the same output;
     * never raises (returns the unfiltered list on any error).
     */
    _inomFilterOrders(orders) {
        try {
            const rule = this.pos && this.pos.accessRule;
            if (!rule || !rule.restrict_salesperson_orders) {
                return orders || [];
            }
            const uid = this.pos && this.pos.user && this.pos.user.id;
            return (orders || []).filter((order) => {
                if (!order) return false;
                const orderUserId =
                    order.user_id && order.user_id.id !== undefined
                        ? order.user_id.id
                        : order.user_id;
                const orderEmpUserId =
                    order.employee_id &&
                    order.employee_id.user_id &&
                    order.employee_id.user_id.id !== undefined
                        ? order.employee_id.user_id.id
                        : (order.employee_id && order.employee_id.user_id) || undefined;
                return orderEmpUserId === uid || orderUserId === uid;
            });
        } catch (e) {
            console.warn("[inom] order filter failed:", e);
            return orders || [];
        }
    },

    // Early-17.0 form: regular method.
    getFilteredOrderList() {
        const parent = super.getFilteredOrderList;
        if (typeof parent !== "function") {
            // The current Odoo version uses the getter form; this
            // override is unused. The companion `filteredOrderList`
            // getter below takes over.
            return [];
        }
        return this._inomFilterOrders(parent.apply(this, arguments));
    },

    // Late-17.0 / 18.x form: getter on the prototype.
    get filteredOrderList() {
        // `super.filteredOrderList` is undefined if the parent uses the
        // method form — in that case we simply return [] here and the
        // method override above is what the parent class will call.
        const parent = super.filteredOrderList;
        if (parent === undefined) {
            return [];
        }
        return this._inomFilterOrders(parent);
    },
});
