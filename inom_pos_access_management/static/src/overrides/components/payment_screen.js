/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";

/**
 * Restrict the payment methods displayed on the POS PaymentScreen
 * according to the logged-in user's `pos.access.rights` rule.
 *
 * Why a getter + setter on the prototype (and not a one-shot setup() patch)
 * -----------------------------------------------------------------------
 * In Odoo 18 `payment_methods_from_config` may exist in TWO shapes
 * depending on the precise sub-version:
 *
 *   (a) A getter declared on PaymentScreen.prototype that recomputes
 *       the list from `this.pos.config.payment_method_ids` on every
 *       read (newer 18.x / saas builds).
 *   (b) A regular instance property assigned during super.setup() to
 *       a one-shot snapshot of the methods (older 18.0 builds).
 *
 * The PaymentScreen template iterates the list with
 *   <t t-foreach="payment_methods_from_config" t-as="paymentMethod" …/>
 * so the value is re-read on every render. A one-shot filter applied
 * in setup() therefore (i) is not reactive, and (ii) in case (a) is
 * silently bypassed because the OWL reactive proxy keeps resolving the
 * prototype getter. That is exactly why the previous implementation
 * appeared to filter "to nothing" — the filtered own-property was
 * defined, but the template kept reading the prototype getter or
 * captured the value at a moment when the allow-list was still empty.
 *
 * To support both shapes transparently we expose this property as an
 * accessor on the prototype:
 *
 *   * The SETTER intercepts the assignment performed by parent's
 *     setup() (case b) and stashes the value in `_inomBasePaymentMethods`.
 *     Without a setter that assignment would throw:
 *       "Cannot set property payment_methods_from_config of #<…>
 *        which has only a getter".
 *
 *   * The GETTER resolves the unfiltered base list — preferring the
 *     stashed value (case b) and falling back to the originally
 *     captured prototype getter (case a) — and applies the access
 *     filter on every read. Because the getter re-evaluates on each
 *     render, OWL reactivity stays naturally in sync.
 *
 * Behaviour matrix:
 *   • restriction OFF / no rule         → original list (Odoo default)
 *   • restriction ON, single method     → only that one button
 *   • restriction ON, multiple methods  → only those buttons
 *   • restriction ON, empty allow-list  → nothing (explicit deny-all)
 *
 * Every other POS flow, screen, button and permission is untouched.
 */

// Capture the original prototype descriptor ONCE, before patching, so
// we can call the original getter reliably regardless of how Odoo's
// patch utility wires up `super` for accessors across versions.
const _origDescriptor = Object.getOwnPropertyDescriptor(
    PaymentScreen.prototype,
    "payment_methods_from_config"
);
const _origGetter =
    _origDescriptor && typeof _origDescriptor.get === "function"
        ? _origDescriptor.get
        : null;

patch(PaymentScreen.prototype, {
    /**
     * Captures whatever parent setup() assigns so the getter below can
     * use it as the unfiltered base list.
     */
    set payment_methods_from_config(value) {
        this._inomBasePaymentMethods = value;
    },

    /**
     * Returns the filtered list of payment methods to the template.
     * Falls back to the unfiltered list whenever no restriction applies.
     */
    get payment_methods_from_config() {
        // ---------- 1. Resolve the unfiltered base list ----------
        let base = [];
        if (Array.isArray(this._inomBasePaymentMethods)) {
            // Case (b): parent's setup() assigned to the property and
            // our setter captured the value.
            base = this._inomBasePaymentMethods;
        } else if (_origGetter) {
            // Case (a): defer to the originally-captured prototype
            // getter. Wrap defensively — never let an internal Odoo
            // change crash the payment screen.
            try {
                const v = _origGetter.call(this);
                if (Array.isArray(v)) {
                    base = v;
                }
            } catch (e) {
                base = [];
            }
        }

        // ---------- 2. Apply the access-rights filter ----------
        try {
            const rule = this.pos && this.pos.accessRule;
            if (!rule || !rule.restrict_payment_method) {
                // Restriction OFF → preserve default Odoo behaviour.
                return base;
            }

            // Normalise the allow-list to a Set of numeric ids, tolerant
            // of both raw-id ([1, 2]) and resolved-record ([{id: 1}, …])
            // representations that the POS data loader may emit.
            const allowedIds = new Set();
            for (const m of rule.restrict_payment_method_ids || []) {
                if (m == null) continue;
                const raw = typeof m === "object" ? m.id : m;
                if (raw == null) continue;
                const n = Number(raw);
                if (Number.isFinite(n)) {
                    allowedIds.add(n);
                }
            }

            // Restriction ON but the allow-list is empty → explicit
            // deny-all (matches the toggle's semantic: "Allow ONLY the
            // selected methods").
            if (allowedIds.size === 0) {
                return [];
            }

            return base.filter(
                (m) => m && allowedIds.has(Number(m.id))
            );
        } catch (e) {
            // Never let our filter break the POS — fall back to the
            // unfiltered list if anything unexpected happens.
            console.warn(
                "[inom_pos_access_management] payment-method filter skipped:",
                e
            );
            return base;
        }
    },
});


// /** @odoo-module **/

// import { patch } from "@web/core/utils/patch";
// import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";

// /**
//  * Restrict the payment methods displayed on the POS PaymentScreen
//  * according to the logged-in user's `pos.access.rights` rule.
//  *
//  * Why a getter + setter on the prototype (and not a one-shot setup() patch)
//  * -----------------------------------------------------------------------
//  * In Odoo 18 `payment_methods_from_config` may exist in TWO shapes
//  * depending on the precise sub-version:
//  *
//  *   (a) A getter declared on PaymentScreen.prototype that recomputes
//  *       the list from `this.pos.config.payment_method_ids` on every
//  *       read (newer 18.x / saas builds).
//  *   (b) A regular instance property assigned during super.setup() to
//  *       a one-shot snapshot of the methods (older 18.0 builds).
//  *
//  * The PaymentScreen template iterates the list with
//  *   <t t-foreach="payment_methods_from_config" t-as="paymentMethod" …/>
//  * so the value is re-read on every render. A one-shot filter applied
//  * in setup() therefore (i) is not reactive, and (ii) in case (a) is
//  * silently bypassed because the OWL reactive proxy keeps resolving the
//  * prototype getter. That is exactly why the previous implementation
//  * appeared to filter "to nothing" — the filtered own-property was
//  * defined, but the template kept reading the prototype getter or
//  * captured the value at a moment when the allow-list was still empty.
//  *
//  * To support both shapes transparently we expose this property as an
//  * accessor on the prototype:
//  *
//  *   * The SETTER intercepts the assignment performed by parent's
//  *     setup() (case b) and stashes the value in `_inomBasePaymentMethods`.
//  *     Without a setter that assignment would throw:
//  *       "Cannot set property payment_methods_from_config of #<…>
//  *        which has only a getter".
//  *
//  *   * The GETTER resolves the unfiltered base list — preferring the
//  *     stashed value (case b) and falling back to the originally
//  *     captured prototype getter (case a) — and applies the access
//  *     filter on every read. Because the getter re-evaluates on each
//  *     render, OWL reactivity stays naturally in sync.
//  *
//  * Behaviour matrix:
//  *   • restriction OFF / no rule         → original list (Odoo default)
//  *   • restriction ON, single method     → only that one button
//  *   • restriction ON, multiple methods  → only those buttons
//  *   • restriction ON, empty allow-list  → nothing (explicit deny-all)
//  *
//  * Every other POS flow, screen, button and permission is untouched.
//  */

// // Capture the original prototype descriptor ONCE, before patching, so
// // we can call the original getter reliably regardless of how Odoo's
// // patch utility wires up `super` for accessors across versions.
// const _origDescriptor = Object.getOwnPropertyDescriptor(
//     PaymentScreen.prototype,
//     "payment_methods_from_config"
// );
// const _origGetter =
//     _origDescriptor && typeof _origDescriptor.get === "function"
//         ? _origDescriptor.get
//         : null;

// patch(PaymentScreen.prototype, {
//     /**
//      * Captures whatever parent setup() assigns so the getter below can
//      * use it as the unfiltered base list.
//      */
//     set payment_methods_from_config(value) {
//         this._inomBasePaymentMethods = value;
//     },

//     /**
//      * Returns the filtered list of payment methods to the template.
//      * Falls back to the unfiltered list whenever no restriction applies.
//      */
//     get payment_methods_from_config() {
//         // ---------- 1. Resolve the unfiltered base list ----------
//         let base = [];
//         if (Array.isArray(this._inomBasePaymentMethods)) {
//             // Case (b): parent's setup() assigned to the property and
//             // our setter captured the value.
//             base = this._inomBasePaymentMethods;
//         } else if (_origGetter) {
//             // Case (a): defer to the originally-captured prototype
//             // getter. Wrap defensively — never let an internal Odoo
//             // change crash the payment screen.
//             try {
//                 const v = _origGetter.call(this);
//                 if (Array.isArray(v)) {
//                     base = v;
//                 }
//             } catch (e) {
//                 base = [];
//             }
//         }

//         // ---------- 2. Apply the access-rights filter ----------
//         try {
//             const rule = this.pos && this.pos.accessRule;
//             if (!rule || !rule.restrict_payment_method) {
//                 // Restriction OFF → preserve default Odoo behaviour.
//                 return base;
//             }

//             // Normalise the allow-list to a Set of numeric ids, tolerant
//             // of both raw-id ([1, 2]) and resolved-record ([{id: 1}, …])
//             // representations that the POS data loader may emit.
//             const allowedIds = new Set();
//             for (const m of rule.restrict_payment_method_ids || []) {
//                 if (m == null) continue;
//                 const raw = typeof m === "object" ? m.id : m;
//                 if (raw == null) continue;
//                 const n = Number(raw);
//                 if (Number.isFinite(n)) {
//                     allowedIds.add(n);
//                 }
//             }

//             // Restriction ON but the allow-list is empty → explicit
//             // deny-all (matches the toggle's semantic: "Allow ONLY the
//             // selected methods").
//             if (allowedIds.size === 0) {
//                 return [];
//             }

//             return base.filter(
//                 (m) => m && allowedIds.has(Number(m.id))
//             );
//         } catch (e) {
//             // Never let our filter break the POS — fall back to the
//             // unfiltered list if anything unexpected happens.
//             console.warn(
//                 "[inom_pos_access_management] payment-method filter skipped:",
//                 e
//             );
//             return base;
//         }
//     },
// });












// /** @odoo-module **/

// import { patch } from "@web/core/utils/patch";
// import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";

// /**
//  * Restrict the payment methods displayed on the POS PaymentScreen
//  * according to the logged-in user's `pos.access.rights` rule.
//  *
//  * Why this shape, and not a getter override?
//  * -----------------------------------------
//  * Odoo 19 declares `payment_methods_from_config` on
//  * PaymentScreen.prototype as a getter only.  Inside the base
//  * `setup()` Odoo assigns to that same name on `this`, which works in
//  * vanilla v19 because the prototype descriptor includes a setter.
//  * Overriding it via `patch(..., { get foo() {} })` removes the
//  * setter and causes:
//  *
//  *     TypeError: Cannot set property payment_methods_from_config of
//  *     #<PaymentScreen> which has only a getter
//  *
//  * So instead of touching the prototype getter, we patch `setup()`:
//  *   1. let super.setup() run untouched (no conflict);
//  *   2. read the now-populated array;
//  *   3. filter it according to the access rule;
//  *   4. shadow the value with an *own* property using
//  *      Object.defineProperty, which bypasses any prototype getter.
//  *
//  * This approach is purely additive – when the rule is off or absent,
//  * we return early and the default Odoo behaviour is preserved exactly.
//  */
// patch(PaymentScreen.prototype, {
//     setup() {
//         super.setup(...arguments);
//         try {
//             this._inomApplyPaymentMethodRestriction();
//         } catch (e) {
//             // Never let our code break the POS lifecycle.
//             console.warn(
//                 "[inom_pos_access_management] payment-method filter skipped:",
//                 e
//             );
//         }
//     },

//     _inomApplyPaymentMethodRestriction() {
//         const rule = this.pos && this.pos.accessRule;
//         if (!rule || !rule.restrict_payment_method) {
//             return; // restriction off → preserve default behaviour
//         }

//         const allowedIds = (rule.restrict_payment_method_ids || []).map(
//             (m) => (m && typeof m === "object" ? m.id : m)
//         );

//         const current = this.payment_methods_from_config;
//         if (!Array.isArray(current)) {
//             return;
//         }

//         // Empty allow-list with restriction ON → show nothing rather
//         // than silently fall back to all methods.
//         const filtered = allowedIds.length
//             ? current.filter((m) => m && allowedIds.includes(m.id))
//             : [];

//         // Shadow with an instance property so we never collide with
//         // the getter declared on the prototype.
//         Object.defineProperty(this, "payment_methods_from_config", {
//             value: filtered,
//             configurable: true,
//             writable: true,
//             enumerable: true,
//         });
//     },
// });
