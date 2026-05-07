/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { PosOrder } from "@point_of_sale/app/models/pos_order";

function calculateRounding(amount, precision) {
    if (!precision || precision <= 0) {
        return { roundedAmount: amount, roundingDiff: 0 };
    }
    const rounded = Math.round(amount / precision) * precision;
    const roundedFixed = parseFloat(rounded.toFixed(2));
    const diff = parseFloat((roundedFixed - amount).toFixed(4));
    return { roundedAmount: roundedFixed, roundingDiff: diff };
}

function getOrderTotal(order) {
    try {
        if (typeof order.get_total_with_tax === "function") {
            return order.get_total_with_tax();
        }
        return order.orderlines.reduce(
            (sum, line) => sum + line.get_price_with_tax(), 0
        );
    } catch (e) {
        return order.totalDue;
    }
}

patch(PosOrder.prototype, {

    setup() {
        super.setup(...arguments);
        this.roundingAmount = this.roundingAmount || 0.0;
        this.isRoundingApplied = this.isRoundingApplied || false;
    },

    export_as_JSON() {
        const json = super.export_as_JSON(...arguments);
        json.rounding_amount = parseFloat(
            Math.abs(this.roundingAmount || 0.0).toFixed(4)
        );
        return json;
    },

    init_from_JSON(json) {
        super.init_from_JSON(...arguments);
        this.roundingAmount = parseFloat(
            Math.abs(json.rounding_amount || 0.0).toFixed(4)
        );
        this.isRoundingApplied = this.roundingAmount > 0;
    },
});

patch(PaymentScreen.prototype, {

    _getRoundingMethod() {
        const config = this.pos.config;
        const allMethods = config.payment_method_ids;
        const roundingMethodProxy = config.rounding_payment_method_id;
        if (!roundingMethodProxy) return undefined;
        return allMethods.find((pm) => pm.id === roundingMethodProxy.id);
    },

    async addNewPaymentLine(paymentMethod) {
        await super.addNewPaymentLine(...arguments);

        const config = this.pos.config;
        if (!config.is_rounding_enabled) return;
        if (config.rounding_type !== 'automatic') return;

        const roundingMethod = this._getRoundingMethod();
        if (!roundingMethod) return;
        if (paymentMethod.id === roundingMethod.id) return;

        const order = this.currentOrder;
        const alreadyHasRounding = order.payment_ids.some(
            (l) => l.payment_method_id.id === roundingMethod.id
        );
        if (alreadyHasRounding) return;

        const orderTotal = getOrderTotal(order);
        const { roundedAmount, roundingDiff } = calculateRounding(
            orderTotal,
            config.rounding_precision || 0.05
        );
        if (Math.abs(roundingDiff) < 0.001) return;

        this._applyRoundingToOrder(
            order, orderTotal, roundedAmount, roundingDiff, roundingMethod
        );
    },

    applyManualRounding() {
        const order = this.currentOrder;
        const config = this.pos.config;

        if (!config.is_rounding_enabled) return;
        if (!config.rounding_payment_method_id) {
            alert("Pehle Settings mein Rounding Payment Method configure karo!");
            return;
        }

        const roundingMethod = this._getRoundingMethod();
        if (!roundingMethod) {
            alert("Rounding Method nahi mili!");
            return;
        }

        const orderTotal = getOrderTotal(order);
        const { roundedAmount, roundingDiff } = calculateRounding(
            orderTotal,
            config.rounding_precision || 0.05
        );
        if (Math.abs(roundingDiff) < 0.001) return;

        this._applyRoundingToOrder(
            order, orderTotal, roundedAmount, roundingDiff, roundingMethod
        );
    },

    _applyRoundingToOrder(order, orderTotal, roundedAmount, roundingDiff, roundingMethod) {
        const nonRoundingLines = order.payment_ids.filter(
            (l) => l.payment_method_id.id !== roundingMethod.id
        );

        this._removeRoundingLine(order, roundingMethod);
        order.addPaymentline(roundingMethod);

        const roundingLine = order.payment_ids.find(
            (l) => l.payment_method_id.id === roundingMethod.id
        );

        // Rounding line = orderTotal - roundedAmount
        // 128.11 - 128.10 = -0.01 ✅
        // 1.04   - 1.05   = -0.01 ✅
        // 162.04 - 162.05 = -0.01 ✅
        const roundingLineAmount = parseFloat(
            (orderTotal - roundedAmount).toFixed(2)
        );

        if (roundingLine) {
            roundingLine.setAmount(roundingLineAmount);
        }

        // Cash = roundedAmount
        if (nonRoundingLines.length > 0) {
            nonRoundingLines[0].setAmount(
                parseFloat(roundedAmount.toFixed(2))
            );
        }

        // Positive amount save karo
        order.roundingAmount = parseFloat(
            Math.abs(roundingLineAmount).toFixed(4)
        );
        order.isRoundingApplied = true;
    },

    _removeRoundingLine(order, roundingMethod) {
        if (!roundingMethod) return;
        const toRemove = order.payment_ids.filter(
            (l) => l.payment_method_id.id === roundingMethod.id
        );
        toRemove.forEach((l) => order.removePaymentline(l));
        order.roundingAmount = 0.0;
        order.isRoundingApplied = false;
    },

    refreshRounding() {
        const order = this.currentOrder;
        if (!order || !order.isRoundingApplied) return;

        const roundingMethod = this._getRoundingMethod();
        if (!roundingMethod) return;

        const orderTotal = getOrderTotal(order);
        const { roundedAmount, roundingDiff } = calculateRounding(
            orderTotal,
            this.pos.config.rounding_precision || 0.05
        );

        if (Math.abs(roundingDiff) < 0.001) {
            this._removeRoundingLine(order, roundingMethod);
            return;
        }

        this._applyRoundingToOrder(
            order, orderTotal, roundedAmount, roundingDiff, roundingMethod
        );
    },

    get isRoundingEnabled() {
        return this.pos.config.is_rounding_enabled || false;
    },

    get isManualRounding() {
        return this.pos.config.rounding_type === 'manual';
    },

    get isRoundingApplied() {
        return this.currentOrder?.isRoundingApplied || false;
    },

});









// /** @odoo-module **/

// import { patch } from "@web/core/utils/patch";
// import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
// import { PosOrder } from "@point_of_sale/app/models/pos_order";

// function calculateRounding(amount, precision) {
//     if (!precision || precision <= 0) {
//         return { roundedAmount: amount, roundingDiff: 0 };
//     }
//     const rounded = Math.round(amount / precision) * precision;
//     const roundedFixed = parseFloat(rounded.toFixed(2));
//     const diff = parseFloat((roundedFixed - amount).toFixed(4));
//     return { roundedAmount: roundedFixed, roundingDiff: diff };
// }

// function getOrderTotal(order) {
//     try {
//         if (typeof order.get_total_with_tax === "function") {
//             return order.get_total_with_tax();
//         }
//         return order.orderlines.reduce(
//             (sum, line) => sum + line.get_price_with_tax(), 0
//         );
//     } catch (e) {
//         return order.totalDue;
//     }
// }

// // ─── ORDER MODEL PATCH ────────────────────────────────────────
// patch(PosOrder.prototype, {

//     setup() {
//         super.setup(...arguments);
//         this.roundingAmount = this.roundingAmount || 0.0;
//         this.isRoundingApplied = this.isRoundingApplied || false;
//     },

//     export_as_JSON() {
//         const json = super.export_as_JSON(...arguments);
//         json.rounding_amount = Math.abs(this.roundingAmount || 0.0);
//         return json;
//     },

//     init_from_JSON(json) {
//         super.init_from_JSON(...arguments);
//         this.roundingAmount = json.rounding_amount || 0.0;
//         this.isRoundingApplied = this.roundingAmount !== 0;
//     },
// });

// // ─── PAYMENT SCREEN PATCH ─────────────────────────────────────
// patch(PaymentScreen.prototype, {

//     _getRoundingMethod() {
//         const config = this.pos.config;
//         const allMethods = config.payment_method_ids;
//         const roundingMethodProxy = config.rounding_payment_method_id;
//         if (!roundingMethodProxy) return undefined;
//         return allMethods.find((pm) => pm.id === roundingMethodProxy.id);
//     },

//     async addNewPaymentLine(paymentMethod) {
//         await super.addNewPaymentLine(...arguments);

//         const config = this.pos.config;
//         if (!config.is_rounding_enabled) return;
//         if (config.rounding_type !== 'automatic') return;

//         const roundingMethod = this._getRoundingMethod();
//         if (!roundingMethod) return;
//         if (paymentMethod.id === roundingMethod.id) return;

//         const order = this.currentOrder;
//         const alreadyHasRounding = order.payment_ids.some(
//             (l) => l.payment_method_id.id === roundingMethod.id
//         );
//         if (alreadyHasRounding) return;

//         const orderTotal = getOrderTotal(order);
//         const { roundedAmount, roundingDiff } = calculateRounding(
//             orderTotal,
//             config.rounding_precision || 0.05
//         );
//         if (Math.abs(roundingDiff) < 0.001) return;

//         this._applyRoundingToOrder(
//             order, orderTotal, roundedAmount, roundingDiff, roundingMethod
//         );
//     },

//     applyManualRounding() {
//         const order = this.currentOrder;
//         const config = this.pos.config;

//         if (!config.is_rounding_enabled) return;
//         if (!config.rounding_payment_method_id) {
//             alert("Pehle Settings mein Rounding Payment Method configure karo!");
//             return;
//         }

//         const roundingMethod = this._getRoundingMethod();
//         if (!roundingMethod) {
//             alert("Rounding Method nahi mili!");
//             return;
//         }

//         const orderTotal = getOrderTotal(order);
//         const { roundedAmount, roundingDiff } = calculateRounding(
//             orderTotal,
//             config.rounding_precision || 0.05
//         );
//         if (Math.abs(roundingDiff) < 0.001) return;

//         this._applyRoundingToOrder(
//             order, orderTotal, roundedAmount, roundingDiff, roundingMethod
//         );
//     },

//     _applyRoundingToOrder(order, orderTotal, roundedAmount, roundingDiff, roundingMethod) {
//         const nonRoundingLines = order.payment_ids.filter(
//             (l) => l.payment_method_id.id !== roundingMethod.id
//         );

//         this._removeRoundingLine(order, roundingMethod);
//         order.addPaymentline(roundingMethod);

//         const roundingLine = order.payment_ids.find(
//             (l) => l.payment_method_id.id === roundingMethod.id
//         );

//         // Rounding line = orderTotal - roundedAmount
//         // 128.11 - 128.10 = -0.01 (negative) ✅
//         // 1.04   - 1.05   = -0.01 (negative) ✅
//         // 162.04 - 162.05 = -0.01 (negative) ✅
//         const roundingLineAmount = parseFloat(
//             (orderTotal - roundedAmount).toFixed(2)
//         );

//         if (roundingLine) {
//             roundingLine.setAmount(roundingLineAmount);
//         }

//         // Cash = roundedAmount
//         // 128.11 → 128.10 ✅
//         // 1.04   → 1.05   ✅
//         // 162.04 → 162.05 ✅
//         if (nonRoundingLines.length > 0) {
//             nonRoundingLines[0].setAmount(
//                 parseFloat(roundedAmount.toFixed(2))
//             );
//         }

//         // Backend mein positive save karo
//         order.roundingAmount = Math.abs(roundingLineAmount);
//         order.isRoundingApplied = true;
//     },

//     _removeRoundingLine(order, roundingMethod) {
//         if (!roundingMethod) return;
//         const toRemove = order.payment_ids.filter(
//             (l) => l.payment_method_id.id === roundingMethod.id
//         );
//         toRemove.forEach((l) => order.removePaymentline(l));
//         order.roundingAmount = 0.0;
//         order.isRoundingApplied = false;
//     },

//     refreshRounding() {
//         const order = this.currentOrder;
//         if (!order || !order.isRoundingApplied) return;

//         const roundingMethod = this._getRoundingMethod();
//         if (!roundingMethod) return;

//         const orderTotal = getOrderTotal(order);
//         const { roundedAmount, roundingDiff } = calculateRounding(
//             orderTotal,
//             this.pos.config.rounding_precision || 0.05
//         );

//         if (Math.abs(roundingDiff) < 0.001) {
//             this._removeRoundingLine(order, roundingMethod);
//             return;
//         }

//         this._applyRoundingToOrder(
//             order, orderTotal, roundedAmount, roundingDiff, roundingMethod
//         );
//     },

//     get isRoundingEnabled() {
//         return this.pos.config.is_rounding_enabled || false;
//     },

//     get isManualRounding() {
//         return this.pos.config.rounding_type === 'manual';
//     },

//     get isRoundingApplied() {
//         return this.currentOrder?.isRoundingApplied || false;
//     },

// });















