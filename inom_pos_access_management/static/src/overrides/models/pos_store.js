/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/services/pos_store";

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

patch(PosStore.prototype, {
    get accessRule() {
        try {
            const rules = this.models["pos.access.rights"]?.getAll?.() || [];
            const uid = this.user?.id;
            const found = rules.find((r) => {
                if (!r || !r.user_id) return false;
                const rUid = r.user_id.id ?? r.user_id;
                return rUid === uid;
            });
            return found || _emptyAccessRule();
        } catch (e) {
            console.warn("[inom_pos_access_management] accessRule lookup failed:", e);
            return _emptyAccessRule();
        }
    },


    
     





    // async setup() {
    //     await super.setup(...arguments);
    //     try {
    //         this._inom_applyAccessClasses();
    //         this._inom_hideNoteButton();
    //         this._inom_hidePricelistButton();
    //         this._inom_hideTransferButton();
    //         this._inom_hideClosePosButton(); // ← add karo
    //     } catch (e) {
    //         console.warn("[inom_pos_access_management] failed to apply CSS classes:", e);
    //     }
    // },



    // async setup() {
    //     await super.setup(...arguments);
    //     try {
    //         this._inom_applyAccessClasses();
    //         this._inom_hideNoteButton();
    //         this._inom_hidePricelistButton();
    //         this._inom_hideTransferButton();
    //         this._inom_hideClosePosButton();
    //         this._inom_hideBackendButton(); // ← add karo
    //     } catch (e) {
    //         console.warn("[inom_pos_access_management] failed to apply CSS classes:", e);
    //     }
    // },







    async setup() {
        await super.setup(...arguments);
        try {
            this._inom_applyAccessClasses();
            this._inom_hideNoteButton();
            this._inom_hidePricelistButton();
            this._inom_hideTransferButton();
            this._inom_hideClosePosButton();
            this._inom_hideBackendButton();
            this._inom_hideCashInOutButton(); // ← add kiya
            this._inom_hideDebugWindow();
            this._inom_hideTipButton();
            this._inom_hideShipLaterButton();
        } catch (e) {
            console.warn("[inom_pos_access_management] failed to apply CSS classes:", e);
        }
    },









    

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





    _inom_hideNoteButton() {
        const rule = this.accessRule;
        if (!rule?.hide_customer_note_button) return;

        const hideNote = () => {
            document.querySelectorAll("button.btn.btn-secondary.btn-lg").forEach((btn) => {
                if (btn.textContent.trim() === "Note") {
                    btn.style.setProperty("display", "none", "important");
                }
            });
        };

        hideNote();
        const observer = new MutationObserver(() => hideNote());
        observer.observe(document.body, { childList: true, subtree: true });
        setTimeout(() => observer.disconnect(), 60000);
    },







    _inom_hidePricelistButton() {
        const rule = this.accessRule;
        if (!rule?.hide_pricelist_button) return;

        const hideBtn = () => {
            document.querySelectorAll("button").forEach((btn) => {
                if (btn.textContent.trim() === "Pricelist") {
                    btn.style.setProperty("display", "none", "important");
                }
            });
        };

        const observer = new MutationObserver(() => hideBtn());
        observer.observe(document.body, { childList: true, subtree: true });
        setTimeout(() => observer.disconnect(), 60000);
    },





    _inom_hideTransferButton() {
        const rule = this.accessRule;
        if (!rule?.hide_transfer_button) return;

        const hideBtn = () => {
            document.querySelectorAll("button").forEach((btn) => {
                if (btn.textContent.trim() === "Transfer / Merge") {
                    btn.style.setProperty("display", "none", "important");
                }
            });
        };

        const observer = new MutationObserver(() => hideBtn());
        observer.observe(document.body, { childList: true, subtree: true });
        setTimeout(() => observer.disconnect(), 60000);
    },



     

    _inom_hideClosePosButton() {
        const rule = this.accessRule;
        if (!rule?.hide_close_pos_button) return;

        const hideBtn = () => {
            // Hamburger menu item hide karo
            document.querySelectorAll(".o-dropdown--menu .o-dropdown--item, .dropdown-item").forEach((item) => {
                if (item.textContent.trim() === "Close Register") {
                    item.style.setProperty("display", "none", "important");
                }
            });
            // Modal button bhi hide karo
            document.querySelectorAll("button").forEach((btn) => {
                if (btn.textContent.trim() === "Close Register") {
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
        if (!rule?.hide_backend_pos_button) return;

        const hideBtn = () => {
            document.querySelectorAll(".o-dropdown--menu .o-dropdown--item, .dropdown-item, .pos-burger-menu-items").forEach((item) => {
                if (item.textContent.trim() === "Backend") {
                    item.style.setProperty("display", "none", "important");
                }
            });
            document.querySelectorAll("button").forEach((btn) => {
                if (btn.textContent.trim() === "Backend") {
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
        if (!rule?.hide_cash_in_out_button) return;
        const hideBtn = () => {
            document.querySelectorAll(".o-dropdown--menu .o-dropdown--item, .dropdown-item, .pos-burger-menu-items").forEach((item) => {
                if (item.textContent.trim() === "Cash In/Out") {
                    item.style.setProperty("display", "none", "important");
                }
            });
            document.querySelectorAll("button").forEach((btn) => {
                if (btn.textContent.trim() === "Cash In/Out") {
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






    // _inom_hideDebugWindow() {
    //     const rule = this.accessRule;
    //     if (!rule?.hide_debug_window) return;
    //     const hideBtn = () => {
    //         document.querySelectorAll(".o-dropdown--menu .o-dropdown--item, .dropdown-item, .pos-burger-menu-items").forEach((item) => {
    //             if (item.textContent.trim() === "Install App") {
    //                 item.style.setProperty("display", "none", "important");
    //             }
    //         });
    //         document.querySelectorAll("button").forEach((btn) => {
    //             if (btn.textContent.trim() === "Install App") {
    //                 btn.style.setProperty("display", "none", "important");
    //             }
    //         });
    //     };
    //     hideBtn();
    //     const interval = setInterval(hideBtn, 50);
    //     setTimeout(() => clearInterval(interval), 120000);
    //     const observer = new MutationObserver(() => hideBtn());
    //     observer.observe(document.body, { childList: true, subtree: true });
    //     setTimeout(() => observer.disconnect(), 120000);
    // },






    _inom_hideDebugWindow() {
        const rule = this.accessRule;
        if (!rule?.hide_debug_window) return;

        // URL se ?debug=1 remove karo
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
            // Hamburger menu items
            document.querySelectorAll(".o-dropdown--menu .o-dropdown--item, .dropdown-item").forEach((item) => {
                const text = item.textContent.trim();
                if (text === "Install App" || text === "Reload Data") {
                    item.style.setProperty("display", "none", "important");
                }
            });
            // Button fallback
            document.querySelectorAll("button").forEach((btn) => {
                const text = btn.textContent.trim();
                if (text === "Install App" || text === "Reload Data") {
                    btn.style.setProperty("display", "none", "important");
                }
            });
            // Bug icon
            document.querySelectorAll(".o_debug_manager, .o_debug_manager_icon").forEach((el) => {
                el.style.setProperty("display", "none", "important");
            });
        };

        hideDebug();
        const interval = setInterval(hideDebug, 50);
        setTimeout(() => clearInterval(interval), 120000);
        const observer = new MutationObserver(() => hideDebug());
        observer.observe(document.body, { childList: true, subtree: true });
        setTimeout(() => observer.disconnect(), 120000);
    },





   // _inom_filterSalespersonOrders() {
   //      const rule = this.accessRule;
   //      console.log("[inom] restrict_salesperson_orders:", rule?.restrict_salesperson_orders);
   //      console.log("[inom] current uid:", this.user?.id);
   //      if (!rule?.restrict_salesperson_orders) return;
   //      const uid = this.user?.id;
   //      try {
   //          const allOrders = this.models["pos.order"]?.getAll?.() || [];
   //          console.log("[inom] total orders before filter:", allOrders.length);
   //          allOrders.forEach(order => {
   //              const orderUid = order.user_id?.id ?? order.user_id;
   //              console.log("[inom] order:", order.name, "user_id:", orderUid, "uid:", uid, "match:", orderUid === uid);
   //              if (orderUid !== uid) {
   //                  this.models["pos.order"]?.delete?.(order);
   //              }
   //          });
   //          console.log("[inom] filter done");
   //      } catch(e) {
   //          console.warn("[inom] order filter failed:", e);
   //      }
   //  },






    // _inom_filterSalespersonOrders() {
    //     const rule = this.accessRule;
    //     if (!rule?.restrict_salesperson_orders) return;
    //     const uid = this.user?.id;
    //     try {
    //         const orderModel = this.models["pos.order"];
    //         const allOrders = orderModel?.getAll?.() || [];
    //         console.log("[inom] filtering orders, uid:", uid, "total:", allOrders.length);
    //         allOrders.forEach(order => {
    //             const orderUid = order.user_id?.id ?? order.user_id;
    //             console.log("[inom] order:", order.id, "orderUid:", orderUid, "match:", orderUid === uid);
    //             if (orderUid !== uid) {
    //                 // Multiple delete approaches try karo
    //                 try { orderModel.delete(order); } catch(e1) {}
    //                 try { orderModel.delete(order.id); } catch(e2) {}
    //                 try { orderModel.records?.delete?.(order.id); } catch(e3) {}
    //                 try { order.delete?.(); } catch(e4) {}
    //                 try {
    //                     const idx = allOrders.indexOf(order);
    //                     if (idx > -1) allOrders.splice(idx, 1);
    //                 } catch(e5) {}
    //             }
    //         });
    //     } catch(e) {
    //         console.warn("[inom] order filter failed:", e);
    //     }
    // },



  


    _inom_hideTipButton() {
        const rule = this.accessRule;
        if (!rule?.hide_payment_tip_button) return;

        const hideBtn = () => {
            document.querySelectorAll(".payment-screen button").forEach((btn) => {
                const text = btn.textContent.trim();
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
        if (!rule?.hide_payment_ship_later_button) return;

        const hideBtn = () => {
            document.querySelectorAll(".payment-screen button").forEach((btn) => {
                const text = btn.textContent.trim();
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



























    _inom_scheduleNumpadPatch(rule) {
        const needsPatch =
            rule.disable_price_button ||
            rule.disable_qty_button ||
            rule.disable_discount_button ||
            rule.disable_plus_minus_button;

        if (!needsPatch) return;

        const applyDisable = () => {
            const numpad = document.querySelector(".numpad");
            if (!numpad) return;
            const buttons = numpad.querySelectorAll("button");
            buttons.forEach((btn) => {
                const text = (btn.textContent || "").trim();
                if (rule.disable_price_button && text === "Price") {
                    btn.disabled = true;
                    btn.style.opacity = "0.4";
                    btn.style.pointerEvents = "none";
                }
                if (rule.disable_qty_button && text === "Qty") {
                    btn.disabled = true;
                    btn.style.opacity = "0.4";
                    btn.style.pointerEvents = "none";
                }
                if (
                    rule.disable_discount_button &&
                    (text === "Disc" || text === "%" || text === "Discount")
                ) {
                    btn.disabled = true;
                    btn.style.opacity = "0.4";
                    btn.style.pointerEvents = "none";
                }
                if (
                    rule.disable_plus_minus_button &&
                    (text === "+/-" || text === "±")
                ) {
                    btn.disabled = true;
                    btn.style.opacity = "0.4";
                    btn.style.pointerEvents = "none";
                }
            });
        };

        applyDisable();
        const observer = new MutationObserver(() => applyDisable());
        observer.observe(document.body, { childList: true, subtree: true });
        setTimeout(() => observer.disconnect(), 30000);
    },

    isPosCategoryHidden(categoryId) {
        const rule = this.accessRule;
        if (!rule.restrict_pos_categories) return false;
        const hidden = rule.restrict_pos_category_ids || [];
        return hidden.some((c) => (c?.id ?? c) === categoryId);
    },

    isPaymentMethodAllowed(methodId) {
        const rule = this.accessRule;
        if (!rule.restrict_payment_method) return true;
        const allowed = rule.restrict_payment_method_ids || [];
        if (!allowed.length) return false;
        return allowed.some((m) => (m?.id ?? m) === methodId);
    },
});

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




