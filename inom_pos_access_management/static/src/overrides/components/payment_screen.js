/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
// Same module path in Odoo 17 and Odoo 18.
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";

/**
 * ============================================================================
 * Restrict the payment methods shown on the POS PaymentScreen
 * according to the current user's `pos.access.rights` rule.
 * ============================================================================
 *
 * Why this rewrite (Odoo-17 specific)
 * -----------------------------------
 * The previous implementation tried to intercept the
 * `payment_methods_from_config` assignment by installing a `get`/`set`
 * accessor pair on `PaymentScreen.prototype`. That approach relied on
 * JavaScript's prototype-setter mechanism kicking in when the parent
 * `setup()` did `this.payment_methods_from_config = …`.
 *
 * In Odoo 17 that interception is unreliable: depending on the exact
 * sub-version the property ends up being created as an *own property*
 * of the instance (via OWL's component-init order, class-field
 * semantics, or the `patch()` utility's accessor-handling). Once it
 * lives as an own property on the instance, standard JS property
 * lookup **shadows** the prototype getter entirely, so the filtered
 * getter never fires and the template iterates the unfiltered list —
 * which is exactly the bug being fixed (all payment methods visible
 * even when "Restrict Payment Methods" is ON).
 *
 * The new strategy below has zero dependence on the accessor
 * mechanism:
 *
 *   1. Patch `setup()` only. Run AFTER `super.setup()`.
 *   2. At that point `this.payment_methods_from_config` is fully
 *      computed and readable through ordinary property access —
 *      regardless of whether Odoo stored it as an instance own
 *      property OR as a prototype getter. JS resolves both
 *      transparently.
 *   3. Filter the list according to the access rule.
 *   4. Re-install the *filtered* list as an own property on the
 *      instance via `Object.defineProperty`. Own properties always
 *      win over prototype properties in JS lookup, so every
 *      subsequent template render naturally reads the filtered list
 *      with no extra plumbing.
 *
 * Behaviour matrix (unchanged from the original spec):
 *   • restriction OFF / no rule           → original list (Odoo default)
 *   • restriction ON, single method picked → only that one button
 *   • restriction ON, multiple methods    → only those buttons
 *   • restriction ON, empty allow-list    → nothing (explicit deny-all)
 *
 * Odoo-17 vs Odoo-18 data-shape compatibility
 * --------------------------------------------
 * `restrict_payment_method_ids` arrives:
 *   • from Odoo 17 `search_read` as raw integer ids   → `[3]`
 *   • from Odoo 18 `pos.load.mixin` as resolved recs  → `[{id:3, …}]`
 *   • theoretically as Many2one tuples                → `[[3, "Cash"]]`
 *
 * `_normalizeIds()` accepts all three shapes — the file remains
 * binary-compatible across Odoo 17 and 18 with no conditional code.
 * ============================================================================
 */

/**
 * Normalise the raw Many2many payload into a Set<number> of allowed ids.
 * Tolerant of every shape Odoo can produce here.
 */
function _normalizeIds(rawList) {
    const ids = new Set();
    for (const item of rawList || []) {
        if (item == null) continue;
        let id;
        if (Array.isArray(item)) {
            // search_read tuple form: [id, name]
            id = item[0];
        } else if (typeof item === "object") {
            // resolved record form: {id, …}
            id = item.id;
        } else {
            // raw integer / string id
            id = item;
        }
        const n = Number(id);
        if (Number.isFinite(n)) {
            ids.add(n);
        }
    }
    return ids;
}

patch(PaymentScreen.prototype, {

    /**
     * Run AFTER the parent setup() so `this.payment_methods_from_config`
     * is already populated by Odoo's stock logic. We then read it,
     * filter it, and install the filtered list as an own property.
     */
    setup() {
        super.setup(...arguments);
        try {
            this._inom_applyPaymentMethodRestriction();
        } catch (e) {
            // Never let our filter break the POS — fall back to the
            // unfiltered default if anything unexpected happens.
            console.warn(
                "[inom_pos_access_management] payment-method filter skipped:",
                e
            );
        }
    },

    /**
     * Single, isolated method responsible for the entire restriction:
     *   – look up the access rule for the current user;
     *   – if the toggle is OFF, do nothing (preserve Odoo default);
     *   – if the toggle is ON, build the allowed-id set and rewrite
     *     `payment_methods_from_config` as a filtered own property on
     *     THIS instance.
     */
    _inom_applyPaymentMethodRestriction() {
        const rule = this.pos && this.pos.accessRule;

        // Restriction OFF or no rule for this user → leave Odoo's
        // default behaviour completely untouched.
        if (!rule || !rule.restrict_payment_method) {
            return;
        }

        const allowedIds = _normalizeIds(rule.restrict_payment_method_ids);

        // Read whatever the parent class produced for the base list.
        // Standard JS property lookup transparently resolves both
        //   • an own instance property (Odoo 17 typical) AND
        //   • a prototype getter (Odoo 17 alternative / Odoo 18 form)
        // so we don't need to care which it actually is.
        let base;
        try {
            base = this.payment_methods_from_config;
        } catch (e) {
            base = [];
        }
        if (!Array.isArray(base)) {
            base = [];
        }

        // Restriction ON but no method picked → explicit deny-all
        // (matches the toggle's semantic: "allow ONLY selected methods").
        const filtered = allowedIds.size === 0
            ? []
            : base.filter((m) => m && allowedIds.has(Number(m.id)));

        // Install the filtered list as an OWN property on this instance.
        // Own properties shadow any prototype accessor, so every
        // subsequent template render naturally picks up the filtered
        // list — no reactivity plumbing required because the list of
        // payment methods is determined at session start and does not
        // change while a single payment screen is open.
        Object.defineProperty(this, "payment_methods_from_config", {
            value: filtered,
            writable: true,
            configurable: true,
            enumerable: true,
        });
    },
});





// /** @odoo-module **/

// import { patch } from "@web/core/utils/patch";
// // Same module path in Odoo 17 and Odoo 18.
// import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";

// /**
//  * Restrict the payment methods displayed on the POS PaymentScreen
//  * according to the logged-in user's `pos.access.rights` rule.
//  *
//  * Why a getter + setter on the prototype (and not a one-shot setup() patch)
//  * -----------------------------------------------------------------------
//  * In Odoo 17 (and 18) `payment_methods_from_config` may exist in TWO shapes
//  * depending on the exact sub-version:
//  *
//  *   (a) A getter declared on PaymentScreen.prototype that recomputes the
//  *       list from `this.pos.config.payment_method_ids` on every read
//  *       (the prevailing form in late-17.0 and 18.x).
//  *   (b) A regular instance property assigned during super.setup() to a
//  *       one-shot snapshot of the methods (some older 17.0 builds).
//  *
//  * The PaymentScreen template iterates the list with
//  *   <t t-foreach="payment_methods_from_config" t-as="paymentMethod" …/>
//  * so the value is re-read on every render. A one-shot filter applied in
//  * setup() therefore (i) is not reactive, and (ii) in case (a) is silently
//  * bypassed because the OWL reactive proxy keeps resolving the prototype
//  * getter.
//  *
//  * To support both shapes transparently we expose this property as an
//  * accessor on the prototype:
//  *
//  *   * The SETTER intercepts the assignment performed by parent's
//  *     setup() (case b) and stashes the value in `_inomBasePaymentMethods`.
//  *     Without a setter, that assignment would throw:
//  *       "Cannot set property payment_methods_from_config of #<…>
//  *        which has only a getter".
//  *
//  *   * The GETTER resolves the unfiltered base list — preferring the
//  *     stashed value (case b) and falling back to the originally
//  *     captured prototype getter (case a) — and applies the access
//  *     filter on every read. Because the getter re-evaluates on each
//  *     render, OWL reactivity stays naturally in sync.
//  *
//  * Odoo-17 specific point
//  * ----------------------
//  * In Odoo 17 the `restrict_payment_method_ids` field arrives from
//  * `search_read` as a raw array of integer ids (e.g. `[1, 2]`), whereas
//  * Odoo 18 produces resolved record objects (`[{id: 1}, {id: 2}]`).
//  * The normalisation loop below transparently accepts BOTH shapes — so
//  * the file is binary-compatible between the two versions and no
//  * conditional code is needed.
//  *
//  * Behaviour matrix:
//  *   • restriction OFF / no rule         → original list (Odoo default)
//  *   • restriction ON, single method     → only that one button
//  *   • restriction ON, multiple methods  → only those buttons
//  *   • restriction ON, empty allow-list  → nothing (explicit deny-all)
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
//      * use it as the unfiltered base list (case b above).
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
//             // of BOTH the raw-id shape produced by Odoo-17 `search_read`
//             // (`[1, 2]`) and the resolved-record shape produced by the
//             // Odoo-18 `pos.load.mixin` data loader (`[{id:1}, …]`).
//             const allowedIds = new Set();
//             for (const m of rule.restrict_payment_method_ids || []) {
//                 if (m == null) continue;
//                 const raw = typeof m === "object" ? (Array.isArray(m) ? m[0] : m.id) : m;
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
