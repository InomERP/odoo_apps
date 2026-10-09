import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";

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
    return order.totalDue;
}

patch(PaymentScreen.prototype, {

    get configPaymentMethods() {
        // Show the rounding method right after the cash method(s)
        const methods = [...(super.configPaymentMethods || [])];
        const roundingId = this.pos.config.rounding_payment_method_id?.id;
        const index = methods.findIndex((pm) => pm.id === roundingId);
        if (index === -1) return methods;
        const [rounding] = methods.splice(index, 1);
        let insertAt = 0;
        methods.forEach((pm, i) => {
            if (pm.type === "cash") insertAt = i + 1;
        });
        methods.splice(insertAt, 0, rounding);
        return methods;
    },

    _getRoundingMethod() {
        const config = this.pos.config;
        const allMethods = config.payment_method_ids;
        const roundingMethodProxy = config.rounding_payment_method_id;
        if (!roundingMethodProxy) return undefined;
        return allMethods.find((pm) => pm.id === roundingMethodProxy.id);
    },

    _getRoundingLines(order, roundingMethod) {
        if (!roundingMethod) return [];
        return order.payment_ids.filter(
            (l) => l.payment_method_id.id === roundingMethod.id
        );
    },

    async addNewPaymentLine(paymentMethod) {
        const result = await super.addNewPaymentLine(...arguments);
        if (!result) return result;

        const config = this.pos.config;
        if (!config.is_rounding_enabled) return result;
        if (config.rounding_type !== 'automatic') return result;

        const roundingMethod = this._getRoundingMethod();
        if (!roundingMethod) return result;
        if (paymentMethod.id === roundingMethod.id) return result;

        const order = this.currentOrder;
        if (this._getRoundingLines(order, roundingMethod).length) return result;

        const orderTotal = getOrderTotal(order);
        const { roundedAmount, roundingDiff } = calculateRounding(
            orderTotal,
            config.rounding_precision || 0.05
        );
        if (Math.abs(roundingDiff) < 0.001) return result;

        this._applyRoundingToOrder(
            order, orderTotal, roundedAmount, roundingDiff, roundingMethod
        );
        return result;
    },

    applyManualRounding() {
        const order = this.currentOrder;
        const config = this.pos.config;

        if (!config.is_rounding_enabled) return;
        if (!config.rounding_payment_method_id) {
            this.dialog.add(AlertDialog, {
                title: _t("Rounding"),
                body: _t("Pehle Settings mein Rounding Payment Method configure karo!"),
            });
            return;
        }

        const roundingMethod = this._getRoundingMethod();
        if (!roundingMethod) {
            this.dialog.add(AlertDialog, {
                title: _t("Rounding"),
                body: _t("Rounding Method nahi mili!"),
            });
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
        const result = order.addPaymentline(roundingMethod);
        const roundingLine = result?.status ? result.data : undefined;

        // Rounding line = orderTotal - roundedAmount
        // 128.11 - 128.10 = 0.01
        // 1.04   - 1.05   = -0.01
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
            // Keep the numpad on the real payment line, not the rounding one
            order.selectPaymentline(nonRoundingLines[0]);
            this.numberBuffer.reset();
        }
    },

    _removeRoundingLine(order, roundingMethod) {
        this._getRoundingLines(order, roundingMethod).forEach(
            (l) => order.removePaymentline(l)
        );
    },

    refreshRounding() {
        const order = this.currentOrder;
        if (!order || !this.isRoundingApplied) return;

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
        // Derived from the payment lines so it survives reloads / order switches
        const order = this.currentOrder;
        if (!order) return false;
        return this._getRoundingLines(order, this._getRoundingMethod()).length > 0;
    },

});
