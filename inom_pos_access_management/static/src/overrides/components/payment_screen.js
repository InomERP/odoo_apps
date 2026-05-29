/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";

/**
 * Restrict the payment methods displayed on the POS PaymentScreen
 * according to the logged-in user's `pos.access.rights` rule.
 *
 * Why this shape, and not a getter override?
 * -----------------------------------------
 * Odoo 19 declares `payment_methods_from_config` on
 * PaymentScreen.prototype as a getter only.  Inside the base
 * `setup()` Odoo assigns to that same name on `this`, which works in
 * vanilla v19 because the prototype descriptor includes a setter.
 * Overriding it via `patch(..., { get foo() {} })` removes the
 * setter and causes:
 *
 *     TypeError: Cannot set property payment_methods_from_config of
 *     #<PaymentScreen> which has only a getter
 *
 * So instead of touching the prototype getter, we patch `setup()`:
 *   1. let super.setup() run untouched (no conflict);
 *   2. read the now-populated array;
 *   3. filter it according to the access rule;
 *   4. shadow the value with an *own* property using
 *      Object.defineProperty, which bypasses any prototype getter.
 *
 * This approach is purely additive – when the rule is off or absent,
 * we return early and the default Odoo behaviour is preserved exactly.
 */
patch(PaymentScreen.prototype, {
    setup() {
        super.setup(...arguments);
        try {
            this._inomApplyPaymentMethodRestriction();
        } catch (e) {
            // Never let our code break the POS lifecycle.
            console.warn(
                "[inom_pos_access_management] payment-method filter skipped:",
                e
            );
        }
    },

    _inomApplyPaymentMethodRestriction() {
        const rule = this.pos && this.pos.accessRule;
        if (!rule || !rule.restrict_payment_method) {
            return; // restriction off → preserve default behaviour
        }

        const allowedIds = (rule.restrict_payment_method_ids || []).map(
            (m) => (m && typeof m === "object" ? m.id : m)
        );

        const current = this.payment_methods_from_config;
        if (!Array.isArray(current)) {
            return;
        }

        // Empty allow-list with restriction ON → show nothing rather
        // than silently fall back to all methods.
        const filtered = allowedIds.length
            ? current.filter((m) => m && allowedIds.includes(m.id))
            : [];

        // Shadow with an instance property so we never collide with
        // the getter declared on the prototype.
        Object.defineProperty(this, "payment_methods_from_config", {
            value: filtered,
            configurable: true,
            writable: true,
            enumerable: true,
        });
    },
});
