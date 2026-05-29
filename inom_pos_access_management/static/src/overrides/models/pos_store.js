/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
// PosStore is at the same module path in Odoo 17 and Odoo 18.
import { PosStore } from "@point_of_sale/app/store/pos_store";

/**
 * Odoo-17 migration notes for this file
 * =====================================
 *
 * 1. Data ingestion
 *    -----------
 *    In Odoo 18 custom records arrive through the `pos.load.mixin`
 *    machinery and are exposed as `this.models['pos.access.rights']`
 *    with a `.getAll()` helper.  Odoo 17 does not have that registry:
 *    custom records arrive as a plain key on the `loadedData` argument
 *    of `PosStore._processData(loadedData)` and need to be stashed on
 *    `this` ourselves.  We do that in the `_processData` override
 *    below and expose the array as `this.pos_access_rights`.
 *
 * 2. Many2one shape
 *    -----------
 *    The frontend access rule comes from `search_read`, so
 *    Many2one fields arrive as `[id, display_name]` tuples (not
 *    resolved record objects like in Odoo 18).  The `_m2oId` helper
 *    normalises all three possible shapes (raw int, tuple, object) so
 *    the access-rule lookup keeps working regardless of which Odoo
 *    version this file is loaded on.
 *
 * 3. The rest of the file (DOM-based hide helpers, body-class toggling,
 *    numpad scheduler) is Odoo-version-agnostic and was preserved
 *    intentionally to maintain 100 % feature parity with the Odoo-18
 *    implementation.
 */

// Every flag managed by the access rule — drives the body CSS classes
// consumed by `static/src/overrides/styles/pos_access_rights.css`.
const ACCESS_FLAGS = [
    // Payment (7)
    "hide_payment_button",
    "hide_payment_customer_button",
    "hide_payment_validate_button",
    "hide_payment_tip_button",
    "hide_payment_ship_later_button",
    "hide_payment_invoice_button",
    "restrict_payment_method",
    // Order (3)
    "restrict_pos_categories",
    "hide_delete_order_button",
    "only_show_active_order",
    // Customer (3)
    "hide_customer_button",
    "hide_create_customer_button",
    "hide_save_customer_button",
    // Numpad (5)
    "hide_numpad_buttons",
    "disable_price_button",
    "disable_qty_button",
    "disable_discount_button",
    "disable_plus_minus_button",
    // Action (7)
    "hide_customer_note_button",
    "hide_refund_button",
    "hide_info_button",
    "hide_quotation_button",
    "hide_fiscal_button",
    "hide_pricelist_button",
    "hide_transfer_button",
    // General (4)
    "hide_close_pos_button",
    "hide_backend_pos_button",
    "hide_cash_in_out_button",
    "hide_debug_window",
];

/**
 * Normalise a Many2one value into its numeric id.
 * Tolerant of every shape Odoo can produce here:
 *   • Odoo 17 search_read tuple :  [3, "John Doe"]   → 3
 *   • Odoo 18 resolved record   :  {id: 3, ...}      → 3
 *   • raw integer / string id   :  3 / "3"           → 3
 */
function _m2oId(v) {
    if (v == null || v === false) return undefined;
    if (Array.isArray(v)) return v[0];
    if (typeof v === "object") return v.id;
    return v;
}

patch(PosStore.prototype, {

    // ------------------------------------------------------------------
    // 1. Ingest the pos.access.rights records sent by pos.session
    //    (Odoo-17 data-loading hook).
    // ------------------------------------------------------------------
    async _processData(loadedData) {
        await super._processData(...arguments);
        const raw = loadedData && loadedData["pos.access.rights"];
        this.pos_access_rights = Array.isArray(raw) ? raw : [];
    },

    // ------------------------------------------------------------------
    // 2. The single source of truth for "what's the rule for me?".
    //    Returns either the matching rule or an all-false fallback so
    //    every consumer can call `rule.<flag>` without null checks.
    // ------------------------------------------------------------------
    get accessRule() {
        try {
            const rules = this.pos_access_rights || [];
            const uid = this.user && this.user.id;
            const found = rules.find((r) => {
                if (!r || !r.user_id) return false;
                return _m2oId(r.user_id) === uid;
            });
            return found || _emptyAccessRule();
        } catch (e) {
            console.warn("[inom_pos_access_management] accessRule lookup failed:", e);
            return _emptyAccessRule();
        }
    },

    // ------------------------------------------------------------------
    // 3. Lifecycle hook: applied right after the POS store finishes
    //    loading.  Order of operations identical to the Odoo-18 module.
    // ------------------------------------------------------------------
    async setup() {
        await super.setup(...arguments);
        try {
            this._inom_applyAccessClasses();
            this._inom_hideCustomerButton();
            this._inom_hideCreateCustomerButton();
            this._inom_hideSaveCustomerButton();
            this._inom_hidePaymentCustomerButton();
            this._inom_hideNoteButton();
            this._inom_hideRefundButton();
            this._inom_hideInfoButton();
            this._inom_hideQuotationButton();
            this._inom_hideFiscalButton();
            this._inom_hideTransferButton();
            this._inom_hidePricelistButton();
            this._inom_hideClosePosButton();
            this._inom_hideBackendButton();
            this._inom_hideCashInOutButton();
            this._inom_hideDebugWindow();
            this._inom_hideTipButton();
            this._inom_hideShipLaterButton();
        } catch (e) {
            console.warn("[inom_pos_access_management] failed to apply CSS classes:", e);
        }
    },

    // ------------------------------------------------------------------
    // 4. Body-class toggling (CSS rules in pos_access_rights.css do the
    //    actual hiding).
    // ------------------------------------------------------------------
    _inom_applyAccessClasses() {
        const body = document.body;
        if (!body) return;
        const rule = this.accessRule;
        for (const flag of ACCESS_FLAGS) {
            const cls = "o_pos_ar_" + flag;
            if (rule && rule[flag]) {
                body.classList.add(cls);
            } else {
                body.classList.remove(cls);
            }
        }
        if (rule) {
            this._inom_scheduleNumpadPatch(rule);
        }
    },





    _inom_hideCustomerButton() {
        const rule = this.accessRule;
        if (!rule || !rule.hide_customer_button) return;

        const hideBtn = () => {
            document.querySelectorAll(".control-button.customer-button").forEach((el) => {
                el.style.setProperty("display", "none", "important");
            });
        };

        hideBtn();
        const observer = new MutationObserver(() => hideBtn());
        observer.observe(document.body, { childList: true, subtree: true });
        setTimeout(() => observer.disconnect(), 60000);
    },




    _inom_hideCreateCustomerButton() {
        const rule = this.accessRule;
        if (!rule || !rule.hide_create_customer_button) return;

        const hideBtn = () => {
            document.querySelectorAll("button.new-customer").forEach((el) => {
                el.style.setProperty("display", "none", "important");
            });
        };

        hideBtn();
        const observer = new MutationObserver(() => hideBtn());
        observer.observe(document.body, { childList: true, subtree: true });
        setTimeout(() => observer.disconnect(), 60000);
    },






    _inom_hideSaveCustomerButton() {
        const rule = this.accessRule;
        if (!rule || !rule.hide_save_customer_button) return;

        const hideBtn = () => {
            document.querySelectorAll(".partnerlistscreen .button.highlight, .top-content .button.highlight").forEach((el) => {
                const text = (el.textContent || "").trim();
                if (text === "Save") {
                    el.style.setProperty("display", "none", "important");
                }
            });
        };

        hideBtn();
        const observer = new MutationObserver(() => hideBtn());
        observer.observe(document.body, { childList: true, subtree: true });
        setTimeout(() => observer.disconnect(), 60000);
    },




    _inom_hidePaymentCustomerButton() {
        const rule = this.accessRule;
        if (!rule || !rule.hide_payment_customer_button) return;

        const hideBtn = () => {
            document.querySelectorAll(".payment-screen .button.partner-button").forEach((el) => {
                el.style.setProperty("display", "none", "important");
            });
        };

        hideBtn();
        const observer = new MutationObserver(() => hideBtn());
        observer.observe(document.body, { childList: true, subtree: true });
        setTimeout(() => observer.disconnect(), 60000);
    },










    // ------------------------------------------------------------------
    // 5. Text-based DOM hiders (resilient to Odoo sub-version markup
    //    differences — CSS selectors alone don't always match because
    //    OWL templates change class names between minor releases).
    //
    //    Every method here:
    //      • bails immediately when its flag is off;
    //      • runs an initial pass plus a MutationObserver for re-renders;
    //      • auto-disconnects after a generous timeout to avoid leaking.
    // ------------------------------------------------------------------
    _inom_hideNoteButton() {
        const rule = this.accessRule;
        if (!rule || !rule.hide_customer_note_button) return;

        const hideNote = () => {
            document.querySelectorAll("button").forEach((btn) => {
                const text = (btn.textContent || "").trim();
                if (text === "Internal Note" || text === "Note" || text === "Customer Note") {
                    btn.style.setProperty("display", "none", "important");
                }
            });
        };

        hideNote();
        const observer = new MutationObserver(() => hideNote());
        observer.observe(document.body, { childList: true, subtree: true });
        setTimeout(() => observer.disconnect(), 60000);
    },

    _inom_hideRefundButton() {
        const rule = this.accessRule;
        if (!rule || !rule.hide_refund_button) return;

        const hideBtn = () => {
            document.querySelectorAll("button").forEach((btn) => {
                const text = (btn.textContent || "").trim();
                if (text === "Refund" || text === "Return") {
                    btn.style.setProperty("display", "none", "important");
                }
            });
        };

        hideBtn();
        const observer = new MutationObserver(() => hideBtn());
        observer.observe(document.body, { childList: true, subtree: true });
        setTimeout(() => observer.disconnect(), 60000);
    },

    _inom_hideInfoButton() {
        const rule = this.accessRule;
        if (!rule || !rule.hide_info_button) return;

        const hideBtn = () => {
            document.querySelectorAll("button").forEach((btn) => {
                const text = (btn.textContent || "").trim();
                if (text === "Info" || text === "Product Info") {
                    btn.style.setProperty("display", "none", "important");
                }
            });
        };

        hideBtn();
        const observer = new MutationObserver(() => hideBtn());
        observer.observe(document.body, { childList: true, subtree: true });
        setTimeout(() => observer.disconnect(), 60000);
    },

    // _inom_hideQuotationButton() {
    //     const rule = this.accessRule;
    //     if (!rule || !rule.hide_quotation_button) return;

    //     const hideBtn = () => {
    //         document.querySelectorAll("button").forEach((btn) => {
    //             const text = (btn.textContent || "").trim();
    //             if (text === "Quotation/Order" || text === "Quotation" || text === "Order") {
    //                 btn.style.setProperty("display", "none", "important");
    //             }
    //         });
    //     };

    //     hideBtn();
    //     const observer = new MutationObserver(() => hideBtn());
    //     observer.observe(document.body, { childList: true, subtree: true });
    //     setTimeout(() => observer.disconnect(), 60000);
    // },





    _inom_hideQuotationButton() {
        const rule = this.accessRule;
        if (!rule || !rule.hide_quotation_button) return;

        const hideBtn = () => {
            document.querySelectorAll(".o_sale_order_button").forEach((el) => {
                el.style.setProperty("display", "none", "important");
            });
        };

        hideBtn();
        const observer = new MutationObserver(hideBtn);
        observer.observe(document.body, { childList: true, subtree: true });
    },










    // _inom_hideFiscalButton() {
    //     const rule = this.accessRule;
    //     if (!rule || !rule.hide_fiscal_button) return;

    //     const hideBtn = () => {
    //         document.querySelectorAll("button").forEach((btn) => {
    //             const text = (btn.textContent || "").trim();
    //             if (text === "Tax" || text === "Fiscal Position" || text === "Fiscal") {
    //                 btn.style.setProperty("display", "none", "important");
    //             }
    //         });
    //     };

    //     hideBtn();
    //     const observer = new MutationObserver(() => hideBtn());
    //     observer.observe(document.body, { childList: true, subtree: true });
    //     setTimeout(() => observer.disconnect(), 60000);
    // },




    _inom_hideFiscalButton() {
        const rule = this.accessRule;
        if (!rule || !rule.hide_fiscal_button) return;

        const hideBtn = () => {
            document.querySelectorAll(".o_fiscal_position_button").forEach((el) => {
                el.style.setProperty("display", "none", "important");
            });
        };

        hideBtn();
        const observer = new MutationObserver(hideBtn);
        observer.observe(document.body, { childList: true, subtree: true });
    },











    _inom_hideTransferButton() {
        const rule = this.accessRule;
        if (!rule || !rule.hide_transfer_button) return;

        const hideBtn = () => {
            document.querySelectorAll("button").forEach((btn) => {
                const text = (btn.textContent || "").trim();
                if (text === "Transfer / Merge" || text === "Transfer" || text === "Merge") {
                    btn.style.setProperty("display", "none", "important");
                }
            });
        };

        hideBtn();
        const observer = new MutationObserver(() => hideBtn());
        observer.observe(document.body, { childList: true, subtree: true });
        setTimeout(() => observer.disconnect(), 60000);
    },

    _inom_hidePricelistButton() {
        const rule = this.accessRule;
        if (!rule || !rule.hide_pricelist_button) return;

        const hideBtn = () => {
            document.querySelectorAll("button").forEach((btn) => {
                if ((btn.textContent || "").trim() === "Pricelist") {
                    btn.style.setProperty("display", "none", "important");
                }
            });
        };

        hideBtn();
        const observer = new MutationObserver(() => hideBtn());
        observer.observe(document.body, { childList: true, subtree: true });
        setTimeout(() => observer.disconnect(), 60000);
    },

    _inom_hideClosePosButton() {
        const rule = this.accessRule;
        if (!rule || !rule.hide_close_pos_button) return;

        const hideBtn = () => {
            document.querySelectorAll(
                ".o-dropdown--menu .o-dropdown--item, .dropdown-item"
            ).forEach((item) => {
                if ((item.textContent || "").trim() === "Close Register") {
                    item.style.setProperty("display", "none", "important");
                }
            });
            document.querySelectorAll("button").forEach((btn) => {
                if ((btn.textContent || "").trim() === "Close Register") {
                    btn.style.setProperty("display", "none", "important");
                }
            });
        };

        hideBtn();
        const interval = setInterval(hideBtn, 50);
        setTimeout(() => clearInterval(interval), 120000);
        const observer = new MutationObserver(() => hideBtn());
        observer.observe(document.body, { childList: true, subtree: true });
        setTimeout(() => observer.disconnect(), 120000);
    },

    _inom_hideBackendButton() {
        const rule = this.accessRule;
        if (!rule || !rule.hide_backend_pos_button) return;

        const hideBtn = () => {
            document.querySelectorAll(
                ".o-dropdown--menu .o-dropdown--item, .dropdown-item, .pos-burger-menu-items"
            ).forEach((item) => {
                if ((item.textContent || "").trim() === "Backend") {
                    item.style.setProperty("display", "none", "important");
                }
            });
            document.querySelectorAll("button").forEach((btn) => {
                if ((btn.textContent || "").trim() === "Backend") {
                    btn.style.setProperty("display", "none", "important");
                }
            });
        };

        hideBtn();
        const interval = setInterval(hideBtn, 50);
        setTimeout(() => clearInterval(interval), 120000);
        const observer = new MutationObserver(() => hideBtn());
        observer.observe(document.body, { childList: true, subtree: true });
        setTimeout(() => observer.disconnect(), 120000);
    },

    _inom_hideCashInOutButton() {
        const rule = this.accessRule;
        if (!rule || !rule.hide_cash_in_out_button) return;

        const hideBtn = () => {
            document.querySelectorAll(
                ".o-dropdown--menu .o-dropdown--item, .dropdown-item, .pos-burger-menu-items"
            ).forEach((item) => {
                if ((item.textContent || "").trim() === "Cash In/Out") {
                    item.style.setProperty("display", "none", "important");
                }
            });
            document.querySelectorAll("button").forEach((btn) => {
                if ((btn.textContent || "").trim() === "Cash In/Out") {
                    btn.style.setProperty("display", "none", "important");
                }
            });
        };

        hideBtn();
        const interval = setInterval(hideBtn, 50);
        setTimeout(() => clearInterval(interval), 120000);
        const observer = new MutationObserver(() => hideBtn());
        observer.observe(document.body, { childList: true, subtree: true });
        setTimeout(() => observer.disconnect(), 120000);
    },

    _inom_hideDebugWindow() {
        const rule = this.accessRule;
        if (!rule || !rule.hide_debug_window) return;

        try {
            const url = new URL(window.location.href);
            if (url.searchParams.has("debug")) {
                url.searchParams.delete("debug");
                window.history.replaceState({}, document.title, url.toString());
            }
        } catch (e) {
            console.warn("[inom] debug URL remove failed:", e);
        }

        const hideDebug = () => {
            document.querySelectorAll(
                ".o-dropdown--menu .o-dropdown--item, .dropdown-item"
            ).forEach((item) => {
                const text = (item.textContent || "").trim();
                if (text === "Install App" || text === "Debug Window" || text === "Clear Cache") {
                    item.style.setProperty("display", "none", "important");
                }
            });
            document.querySelectorAll("button").forEach((btn) => {
                const text = (btn.textContent || "").trim();
                if (text === "Install App" || text === "Debug Window" || text === "Clear Cache") {
                    btn.style.setProperty("display", "none", "important");
                }
            });
            document.querySelectorAll(".pos-burger-menu-items li, .burger-menu li").forEach((item) => {
                const text = (item.textContent || "").trim();
                if (text === "Install App" || text === "Debug Window" || text === "Clear Cache") {
                    item.style.setProperty("display", "none", "important");
                }
            });
        };

        hideDebug();
        const interval = setInterval(hideDebug, 50);
        setTimeout(() => clearInterval(interval), 120000);
        const observer = new MutationObserver(() => hideDebug());
        observer.observe(document.body, { childList: true, subtree: true });
        setTimeout(() => observer.disconnect(), 120000);
    },

    _inom_hideTipButton() {
        const rule = this.accessRule;
        if (!rule || !rule.hide_payment_tip_button) return;

        const hideBtn = () => {
            document.querySelectorAll(".payment-screen button").forEach((btn) => {
                const text = (btn.textContent || "").trim();
                if (text === "Tip" || text.includes("Tip")) {
                    btn.style.setProperty("display", "none", "important");
                }
            });
        };

        hideBtn();
        const interval = setInterval(hideBtn, 50);
        setTimeout(() => clearInterval(interval), 120000);
        const observer = new MutationObserver(() => hideBtn());
        observer.observe(document.body, { childList: true, subtree: true });
        setTimeout(() => observer.disconnect(), 120000);
    },

    _inom_hideShipLaterButton() {
        const rule = this.accessRule;
        if (!rule || !rule.hide_payment_ship_later_button) return;

        const hideBtn = () => {
            document.querySelectorAll(".payment-screen button").forEach((btn) => {
                const text = (btn.textContent || "").trim();
                if (text === "Ship Later" || text.includes("Ship Later")) {
                    btn.style.setProperty("display", "none", "important");
                }
            });
        };

        hideBtn();
        const interval = setInterval(hideBtn, 50);
        setTimeout(() => clearInterval(interval), 120000);
        const observer = new MutationObserver(() => hideBtn());
        observer.observe(document.body, { childList: true, subtree: true });
        setTimeout(() => observer.disconnect(), 120000);
    },

    // ------------------------------------------------------------------
    // 6. Numpad mode-button disabler — FIXED for Odoo 17
    //    • persistent MutationObserver (no disconnect timeout)
    //    • case-insensitive text matching
    //    • .numpad + .pos-numpad both covered
    //    • hide_numpad_buttons also included in needsPatch check
    // ------------------------------------------------------------------
    _inom_scheduleNumpadPatch(rule) {
        const needsPatch =
            rule.disable_price_button ||
            rule.disable_qty_button ||
            rule.disable_discount_button ||
            rule.disable_plus_minus_button ||
            rule.hide_numpad_buttons;

        if (!needsPatch) return;

        const _disableBtn = (btn) => {
            btn.disabled = true;
            btn.style.setProperty("opacity", "0.4", "important");
            btn.style.setProperty("pointer-events", "none", "important");
            btn.style.setProperty("cursor", "not-allowed", "important");
        };

        const applyDisable = () => {
            const numpadContainers = document.querySelectorAll(".numpad, .pos-numpad");
            if (!numpadContainers.length) return;

            numpadContainers.forEach((numpad) => {
                const buttons = numpad.querySelectorAll("button");
                buttons.forEach((btn) => {
                    const text = (btn.textContent || "").trim().toLowerCase();

                    // if (rule.disable_price_button) {
                    //     if (
                    //         text === "price" || text === "pr" ||
                    //         btn.getAttribute("name") === "price" ||
                    //         btn.classList.contains("mode-price") ||
                    //         btn.classList.contains("price-button")
                    //     ) {
                    //         _disableBtn(btn);
                    //     }
                    // }


                    if (rule.disable_discount_button) {
                        if (
                            text === "% disc" ||
                            text === "disc" ||
                            text === "%" ||
                            text === "discount" ||
                            text.includes("disc")
                        ) {
                            _disableBtn(btn);
                        }
                    }




                    if (rule.disable_qty_button) {
                        if (
                            text === "qty" || text === "quantity" ||
                            btn.getAttribute("name") === "quantity" ||
                            btn.classList.contains("mode-quantity") ||
                            btn.classList.contains("qty-button")
                        ) {
                            _disableBtn(btn);
                        }
                    }

                    if (rule.disable_discount_button) {
                        if (
                            text === "disc" || text === "%" || text === "discount" ||
                            btn.getAttribute("name") === "discount" ||
                            btn.classList.contains("mode-discount") ||
                            btn.classList.contains("discount-button")
                        ) {
                            _disableBtn(btn);
                        }
                    }

                    if (rule.disable_plus_minus_button) {
                        if (
                            text === "+/-" || text === "±" || text === "sign" ||
                            btn.getAttribute("name") === "sign" ||
                            btn.getAttribute("name") === "+/-" ||
                            btn.classList.contains("numpad-minus") ||
                            btn.classList.contains("o_sign_button") ||
                            btn.classList.contains("plus-minus")
                        ) {
                            _disableBtn(btn);
                        }
                    }
                });
            });
        };

        applyDisable();
        const interval = setInterval(applyDisable, 300);
        setTimeout(() => clearInterval(interval), 5000);

        const observer = new MutationObserver(() => applyDisable());
        observer.observe(document.body, { childList: true, subtree: true });
        // Intentionally no disconnect — persists for full POS session
    },

    // ------------------------------------------------------------------
    // 7. Public helpers consumed by other JS files.
    // ------------------------------------------------------------------
    isPosCategoryHidden(categoryId) {
        const rule = this.accessRule;
        if (!rule.restrict_pos_categories) return false;
        const hidden = rule.restrict_pos_category_ids || [];
        return hidden.some((c) => _m2oId(c) === categoryId);
    },

    isPaymentMethodAllowed(methodId) {
        const rule = this.accessRule;
        if (!rule.restrict_payment_method) return true;
        const allowed = rule.restrict_payment_method_ids || [];
        if (!allowed.length) return false;
        return allowed.some((m) => _m2oId(m) === methodId);
    },
});

// ----------------------------------------------------------------------
// Default rule used when the current user has no active access rule.
// Every flag defaults to false so the standard POS shows unchanged.
// ----------------------------------------------------------------------
function _emptyAccessRule() {
    const r = {
        id: false,
        restrict_salesperson_orders: false,
        restrict_salesperson_customers: false,
        restrict_payment_method_ids: [],
        restrict_pos_category_ids: [],
    };
    for (const f of ACCESS_FLAGS) r[f] = false;
    return r;
}



// /** @odoo-module **/

// import { patch } from "@web/core/utils/patch";
// // PosStore is at the same module path in Odoo 17 and Odoo 18.
// import { PosStore } from "@point_of_sale/app/store/pos_store";

// /**
//  * Odoo-17 migration notes for this file
//  * =====================================
//  *
//  * 1. Data ingestion
//  *    -----------
//  *    In Odoo 18 custom records arrive through the `pos.load.mixin`
//  *    machinery and are exposed as `this.models['pos.access.rights']`
//  *    with a `.getAll()` helper.  Odoo 17 does not have that registry:
//  *    custom records arrive as a plain key on the `loadedData` argument
//  *    of `PosStore._processData(loadedData)` and need to be stashed on
//  *    `this` ourselves.  We do that in the `_processData` override
//  *    below and expose the array as `this.pos_access_rights`.
//  *
//  * 2. Many2one shape
//  *    -----------
//  *    The frontend access rule comes from `search_read`, so
//  *    Many2one fields arrive as `[id, display_name]` tuples (not
//  *    resolved record objects like in Odoo 18).  The `_m2oId` helper
//  *    normalises all three possible shapes (raw int, tuple, object) so
//  *    the access-rule lookup keeps working regardless of which Odoo
//  *    version this file is loaded on.
//  *
//  * 3. The rest of the file (DOM-based hide helpers, body-class toggling,
//  *    numpad scheduler) is Odoo-version-agnostic and was preserved
//  *    intentionally to maintain 100 % feature parity with the Odoo-18
//  *    implementation.
//  */

// // Every flag managed by the access rule — drives the body CSS classes
// // consumed by `static/src/overrides/styles/pos_access_rights.css`.
// const ACCESS_FLAGS = [
//     // Payment (7)
//     "hide_payment_button",
//     "hide_payment_customer_button",
//     "hide_payment_validate_button",
//     "hide_payment_tip_button",
//     "hide_payment_ship_later_button",
//     "hide_payment_invoice_button",
//     "restrict_payment_method",
//     // Order (3)
//     "restrict_pos_categories",
//     "hide_delete_order_button",
//     "only_show_active_order",
//     // Customer (3)
//     "hide_customer_button",
//     "hide_create_customer_button",
//     "hide_save_customer_button",
//     // Numpad (5)
//     "hide_numpad_buttons",
//     "disable_price_button",
//     "disable_qty_button",
//     "disable_discount_button",
//     "disable_plus_minus_button",
//     // Action (7)
//     "hide_customer_note_button",
//     "hide_refund_button",
//     "hide_info_button",
//     "hide_quotation_button",
//     "hide_fiscal_button",
//     "hide_pricelist_button",
//     "hide_transfer_button",
//     // General (4)
//     "hide_close_pos_button",
//     "hide_backend_pos_button",
//     "hide_cash_in_out_button",
//     "hide_debug_window",
// ];

// /**
//  * Normalise a Many2one value into its numeric id.
//  * Tolerant of every shape Odoo can produce here:
//  *   • Odoo 17 search_read tuple :  [3, "John Doe"]   → 3
//  *   • Odoo 18 resolved record   :  {id: 3, ...}      → 3
//  *   • raw integer / string id   :  3 / "3"           → 3
//  */
// function _m2oId(v) {
//     if (v == null || v === false) return undefined;
//     if (Array.isArray(v)) return v[0];
//     if (typeof v === "object") return v.id;
//     return v;
// }

// patch(PosStore.prototype, {

//     // ------------------------------------------------------------------
//     // 1. Ingest the pos.access.rights records sent by pos.session
//     //    (Odoo-17 data-loading hook).
//     // ------------------------------------------------------------------
//     async _processData(loadedData) {
//         await super._processData(...arguments);
//         const raw = loadedData && loadedData["pos.access.rights"];
//         this.pos_access_rights = Array.isArray(raw) ? raw : [];
//     },

//     // ------------------------------------------------------------------
//     // 2. The single source of truth for "what's the rule for me?".
//     //    Returns either the matching rule or an all-false fallback so
//     //    every consumer can call `rule.<flag>` without null checks.
//     // ------------------------------------------------------------------
//     get accessRule() {
//         try {
//             const rules = this.pos_access_rights || [];
//             const uid = this.user && this.user.id;
//             const found = rules.find((r) => {
//                 if (!r || !r.user_id) return false;
//                 return _m2oId(r.user_id) === uid;
//             });
//             return found || _emptyAccessRule();
//         } catch (e) {
//             console.warn("[inom_pos_access_management] accessRule lookup failed:", e);
//             return _emptyAccessRule();
//         }
//     },

//     // ------------------------------------------------------------------
//     // 3. Lifecycle hook: applied right after the POS store finishes
//     //    loading.  Order of operations identical to the Odoo-18 module.
//     // ------------------------------------------------------------------
//     async setup() {
//         await super.setup(...arguments);
//         try {
//             this._inom_applyAccessClasses();
//             this._inom_hideNoteButton();
//             this._inom_hideRefundButton();
//             this._inom_hideInfoButton();
//             this._inom_hideQuotationButton();
//             this._inom_hideFiscalButton();
//             this._inom_hideTransferButton();
//             this._inom_hidePricelistButton();
//             this._inom_hideClosePosButton();
//             this._inom_hideBackendButton();
//             this._inom_hideCashInOutButton();
//             this._inom_hideDebugWindow();
//             this._inom_hideTipButton();
//             this._inom_hideShipLaterButton();
//         } catch (e) {
//             console.warn("[inom_pos_access_management] failed to apply CSS classes:", e);
//         }
//     },

//     // ------------------------------------------------------------------
//     // 4. Body-class toggling (CSS rules in pos_access_rights.css do the
//     //    actual hiding).
//     // ------------------------------------------------------------------
//     _inom_applyAccessClasses() {
//         const body = document.body;
//         if (!body) return;
//         const rule = this.accessRule;
//         for (const flag of ACCESS_FLAGS) {
//             const cls = "o_pos_ar_" + flag;
//             if (rule && rule[flag]) {
//                 body.classList.add(cls);
//             } else {
//                 body.classList.remove(cls);
//             }
//         }
//         if (rule) {
//             this._inom_scheduleNumpadPatch(rule);
//         }
//     },

//     // ------------------------------------------------------------------
//     // 5. Text-based DOM hiders (resilient to Odoo sub-version markup
//     //    differences — CSS selectors alone don't always match because
//     //    OWL templates change class names between minor releases).
//     //
//     //    Every method here:
//     //      • bails immediately when its flag is off;
//     //      • runs an initial pass plus a MutationObserver for re-renders;
//     //      • auto-disconnects after a generous timeout to avoid leaking.
//     // ------------------------------------------------------------------
//     _inom_hideNoteButton() {
//         const rule = this.accessRule;
//         if (!rule || !rule.hide_customer_note_button) return;

//         const hideNote = () => {
//             document.querySelectorAll("button").forEach((btn) => {
//                 const text = (btn.textContent || "").trim();
//                 if (text === "Internal Note" || text === "Note" || text === "Customer Note") {
//                     btn.style.setProperty("display", "none", "important");
//                 }
//             });
//         };

//         hideNote();
//         const observer = new MutationObserver(() => hideNote());
//         observer.observe(document.body, { childList: true, subtree: true });
//         setTimeout(() => observer.disconnect(), 60000);
//     },

//     _inom_hideRefundButton() {
//         const rule = this.accessRule;
//         if (!rule || !rule.hide_refund_button) return;

//         const hideBtn = () => {
//             document.querySelectorAll("button").forEach((btn) => {
//                 const text = (btn.textContent || "").trim();
//                 if (text === "Refund" || text === "Return") {
//                     btn.style.setProperty("display", "none", "important");
//                 }
//             });
//         };

//         hideBtn();
//         const observer = new MutationObserver(() => hideBtn());
//         observer.observe(document.body, { childList: true, subtree: true });
//         setTimeout(() => observer.disconnect(), 60000);
//     },

//     _inom_hideInfoButton() {
//         const rule = this.accessRule;
//         if (!rule || !rule.hide_info_button) return;

//         const hideBtn = () => {
//             document.querySelectorAll("button").forEach((btn) => {
//                 const text = (btn.textContent || "").trim();
//                 if (text === "Info" || text === "Product Info") {
//                     btn.style.setProperty("display", "none", "important");
//                 }
//             });
//         };

//         hideBtn();
//         const observer = new MutationObserver(() => hideBtn());
//         observer.observe(document.body, { childList: true, subtree: true });
//         setTimeout(() => observer.disconnect(), 60000);
//     },

//     _inom_hideQuotationButton() {
//         const rule = this.accessRule;
//         if (!rule || !rule.hide_quotation_button) return;

//         const hideBtn = () => {
//             document.querySelectorAll("button").forEach((btn) => {
//                 const text = (btn.textContent || "").trim();
//                 if (text === "Quotation/Order" || text === "Quotation" || text === "Order") {
//                     btn.style.setProperty("display", "none", "important");
//                 }
//             });
//         };

//         hideBtn();
//         const observer = new MutationObserver(() => hideBtn());
//         observer.observe(document.body, { childList: true, subtree: true });
//         setTimeout(() => observer.disconnect(), 60000);
//     },

//     _inom_hideFiscalButton() {
//         const rule = this.accessRule;
//         if (!rule || !rule.hide_fiscal_button) return;

//         const hideBtn = () => {
//             document.querySelectorAll("button").forEach((btn) => {
//                 const text = (btn.textContent || "").trim();
//                 if (text === "Tax" || text === "Fiscal Position" || text === "Fiscal") {
//                     btn.style.setProperty("display", "none", "important");
//                 }
//             });
//         };

//         hideBtn();
//         const observer = new MutationObserver(() => hideBtn());
//         observer.observe(document.body, { childList: true, subtree: true });
//         setTimeout(() => observer.disconnect(), 60000);
//     },

//     _inom_hideTransferButton() {
//         const rule = this.accessRule;
//         if (!rule || !rule.hide_transfer_button) return;

//         const hideBtn = () => {
//             document.querySelectorAll("button").forEach((btn) => {
//                 const text = (btn.textContent || "").trim();
//                 if (text === "Transfer / Merge" || text === "Transfer" || text === "Merge") {
//                     btn.style.setProperty("display", "none", "important");
//                 }
//             });
//         };

//         hideBtn();
//         const observer = new MutationObserver(() => hideBtn());
//         observer.observe(document.body, { childList: true, subtree: true });
//         setTimeout(() => observer.disconnect(), 60000);
//     },

//     _inom_hidePricelistButton() {
//         const rule = this.accessRule;
//         if (!rule || !rule.hide_pricelist_button) return;

//         const hideBtn = () => {
//             document.querySelectorAll("button").forEach((btn) => {
//                 if ((btn.textContent || "").trim() === "Pricelist") {
//                     btn.style.setProperty("display", "none", "important");
//                 }
//             });
//         };

//         hideBtn();
//         const observer = new MutationObserver(() => hideBtn());
//         observer.observe(document.body, { childList: true, subtree: true });
//         setTimeout(() => observer.disconnect(), 60000);
//     },

//     _inom_hideClosePosButton() {
//         const rule = this.accessRule;
//         if (!rule || !rule.hide_close_pos_button) return;

//         const hideBtn = () => {
//             document.querySelectorAll(
//                 ".o-dropdown--menu .o-dropdown--item, .dropdown-item"
//             ).forEach((item) => {
//                 if ((item.textContent || "").trim() === "Close Register") {
//                     item.style.setProperty("display", "none", "important");
//                 }
//             });
//             document.querySelectorAll("button").forEach((btn) => {
//                 if ((btn.textContent || "").trim() === "Close Register") {
//                     btn.style.setProperty("display", "none", "important");
//                 }
//             });
//         };

//         hideBtn();
//         const interval = setInterval(hideBtn, 50);
//         setTimeout(() => clearInterval(interval), 120000);
//         const observer = new MutationObserver(() => hideBtn());
//         observer.observe(document.body, { childList: true, subtree: true });
//         setTimeout(() => observer.disconnect(), 120000);
//     },

//     _inom_hideBackendButton() {
//         const rule = this.accessRule;
//         if (!rule || !rule.hide_backend_pos_button) return;

//         const hideBtn = () => {
//             document.querySelectorAll(
//                 ".o-dropdown--menu .o-dropdown--item, .dropdown-item, .pos-burger-menu-items"
//             ).forEach((item) => {
//                 if ((item.textContent || "").trim() === "Backend") {
//                     item.style.setProperty("display", "none", "important");
//                 }
//             });
//             document.querySelectorAll("button").forEach((btn) => {
//                 if ((btn.textContent || "").trim() === "Backend") {
//                     btn.style.setProperty("display", "none", "important");
//                 }
//             });
//         };

//         hideBtn();
//         const interval = setInterval(hideBtn, 50);
//         setTimeout(() => clearInterval(interval), 120000);
//         const observer = new MutationObserver(() => hideBtn());
//         observer.observe(document.body, { childList: true, subtree: true });
//         setTimeout(() => observer.disconnect(), 120000);
//     },

//     _inom_hideCashInOutButton() {
//         const rule = this.accessRule;
//         if (!rule || !rule.hide_cash_in_out_button) return;

//         const hideBtn = () => {
//             document.querySelectorAll(
//                 ".o-dropdown--menu .o-dropdown--item, .dropdown-item, .pos-burger-menu-items"
//             ).forEach((item) => {
//                 if ((item.textContent || "").trim() === "Cash In/Out") {
//                     item.style.setProperty("display", "none", "important");
//                 }
//             });
//             document.querySelectorAll("button").forEach((btn) => {
//                 if ((btn.textContent || "").trim() === "Cash In/Out") {
//                     btn.style.setProperty("display", "none", "important");
//                 }
//             });
//         };

//         hideBtn();
//         const interval = setInterval(hideBtn, 50);
//         setTimeout(() => clearInterval(interval), 120000);
//         const observer = new MutationObserver(() => hideBtn());
//         observer.observe(document.body, { childList: true, subtree: true });
//         setTimeout(() => observer.disconnect(), 120000);
//     },

//     _inom_hideDebugWindow() {
//         const rule = this.accessRule;
//         if (!rule || !rule.hide_debug_window) return;

//         // Strip ?debug=... from the URL so the cashier can't re-enter
//         // developer mode by reloading.
//         try {
//             const url = new URL(window.location.href);
//             if (url.searchParams.has("debug")) {
//                 url.searchParams.delete("debug");
//                 window.history.replaceState({}, document.title, url.toString());
//             }
//         } catch (e) {
//             console.warn("[inom] debug URL remove failed:", e);
//         }

//         const hideDebug = () => {
//             document.querySelectorAll(
//                 ".o-dropdown--menu .o-dropdown--item, .dropdown-item"
//             ).forEach((item) => {
//                 const text = (item.textContent || "").trim();
//                 if (text === "Install App" || text === "Debug Window" || text === "Clear Cache") {
//                     item.style.setProperty("display", "none", "important");
//                 }
//             });
//             document.querySelectorAll("button").forEach((btn) => {
//                 const text = (btn.textContent || "").trim();
//                 if (text === "Install App" || text === "Debug Window" || text === "Clear Cache") {
//                     btn.style.setProperty("display", "none", "important");
//                 }
//             });
//             document.querySelectorAll(".pos-burger-menu-items li, .burger-menu li").forEach((item) => {
//                 const text = (item.textContent || "").trim();
//                 if (text === "Install App" || text === "Debug Window" || text === "Clear Cache") {
//                     item.style.setProperty("display", "none", "important");
//                 }
//             });
//         };

//         hideDebug();
//         const interval = setInterval(hideDebug, 50);
//         setTimeout(() => clearInterval(interval), 120000);
//         const observer = new MutationObserver(() => hideDebug());
//         observer.observe(document.body, { childList: true, subtree: true });
//         setTimeout(() => observer.disconnect(), 120000);
//     },

//     _inom_hideTipButton() {
//         const rule = this.accessRule;
//         if (!rule || !rule.hide_payment_tip_button) return;

//         const hideBtn = () => {
//             document.querySelectorAll(".payment-screen button").forEach((btn) => {
//                 const text = (btn.textContent || "").trim();
//                 if (text === "Tip" || text.includes("Tip")) {
//                     btn.style.setProperty("display", "none", "important");
//                 }
//             });
//         };

//         hideBtn();
//         const interval = setInterval(hideBtn, 50);
//         setTimeout(() => clearInterval(interval), 120000);
//         const observer = new MutationObserver(() => hideBtn());
//         observer.observe(document.body, { childList: true, subtree: true });
//         setTimeout(() => observer.disconnect(), 120000);
//     },

//     _inom_hideShipLaterButton() {
//         const rule = this.accessRule;
//         if (!rule || !rule.hide_payment_ship_later_button) return;

//         const hideBtn = () => {
//             document.querySelectorAll(".payment-screen button").forEach((btn) => {
//                 const text = (btn.textContent || "").trim();
//                 if (text === "Ship Later" || text.includes("Ship Later")) {
//                     btn.style.setProperty("display", "none", "important");
//                 }
//             });
//         };

//         hideBtn();
//         const interval = setInterval(hideBtn, 50);
//         setTimeout(() => clearInterval(interval), 120000);
//         const observer = new MutationObserver(() => hideBtn());
//         observer.observe(document.body, { childList: true, subtree: true });
//         setTimeout(() => observer.disconnect(), 120000);
//     },

//     // ------------------------------------------------------------------
//     // 6. Numpad mode-button disabler — picks the right buttons by their
//     //    visible label, then locks them via inline style + `disabled`.
//     // ------------------------------------------------------------------
//     _inom_scheduleNumpadPatch(rule) {
//         const needsPatch =
//             rule.disable_price_button ||
//             rule.disable_qty_button ||
//             rule.disable_discount_button ||
//             rule.disable_plus_minus_button;

//         if (!needsPatch) return;

//         const applyDisable = () => {
//             const numpad = document.querySelector(".numpad");
//             if (!numpad) return;
//             const buttons = numpad.querySelectorAll("button");
//             buttons.forEach((btn) => {
//                 const text = (btn.textContent || "").trim();
//                 if (rule.disable_price_button && text === "Price") {
//                     btn.disabled = true;
//                     btn.style.opacity = "0.4";
//                     btn.style.pointerEvents = "none";
//                 }
//                 if (rule.disable_qty_button && text === "Qty") {
//                     btn.disabled = true;
//                     btn.style.opacity = "0.4";
//                     btn.style.pointerEvents = "none";
//                 }
//                 if (
//                     rule.disable_discount_button &&
//                     (text === "Disc" || text === "%" || text === "Discount")
//                 ) {
//                     btn.disabled = true;
//                     btn.style.opacity = "0.4";
//                     btn.style.pointerEvents = "none";
//                 }
//                 if (
//                     rule.disable_plus_minus_button &&
//                     (text === "+/-" || text === "±")
//                 ) {
//                     btn.disabled = true;
//                     btn.style.opacity = "0.4";
//                     btn.style.pointerEvents = "none";
//                 }
//             });
//         };

//         applyDisable();
//         const observer = new MutationObserver(() => applyDisable());
//         observer.observe(document.body, { childList: true, subtree: true });
//         setTimeout(() => observer.disconnect(), 30000);
//     },

//     // ------------------------------------------------------------------
//     // 7. Public helpers consumed by other JS files.
//     //    `c?.id ?? c` happens to also unwrap tuples in JS because
//     //    arrays don't have an `.id` property; `_m2oId` is the explicit,
//     //    fully tolerant version we use everywhere internally.
//     // ------------------------------------------------------------------
//     isPosCategoryHidden(categoryId) {
//         const rule = this.accessRule;
//         if (!rule.restrict_pos_categories) return false;
//         const hidden = rule.restrict_pos_category_ids || [];
//         return hidden.some((c) => _m2oId(c) === categoryId);
//     },

//     isPaymentMethodAllowed(methodId) {
//         const rule = this.accessRule;
//         if (!rule.restrict_payment_method) return true;
//         const allowed = rule.restrict_payment_method_ids || [];
//         if (!allowed.length) return false;
//         return allowed.some((m) => _m2oId(m) === methodId);
//     },
// });

// // ----------------------------------------------------------------------
// // Default rule used when the current user has no active access rule.
// // Every flag defaults to ``false`` so the standard POS shows unchanged.
// // ----------------------------------------------------------------------
// function _emptyAccessRule() {
//     const r = {
//         id: false,
//         restrict_salesperson_orders: false,
//         restrict_salesperson_customers: false,
//         restrict_payment_method_ids: [],
//         restrict_pos_category_ids: [],
//     };
//     for (const f of ACCESS_FLAGS) r[f] = false;
//     return r;
// }
