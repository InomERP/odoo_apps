/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { PosStore } from "@point_of_sale/app/services/pos_store";

export const ACCESS_FLAGS = [
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

export function emptyAccessRule() {
    const r = {
        id: false,
        restrict_salesperson_orders: false,
        restrict_salesperson_customers: false,
        restrict_payment_method_ids: [],
        restrict_pos_category_ids: [],
    };
    for (const f of ACCESS_FLAGS) {
        r[f] = false;
    }
    return r;
}

/**
 * Return the pos.access.rights record of the logged-in user, or an empty
 * rule (all flags off) when there is none.
 */
export function getAccessRule(models) {
    try {
        const rules = models?.["pos.access.rights"]?.getAll?.() || [];
        const uid = models?.["res.users"]?.getFirst?.()?.id;
        const found = rules.find((r) => {
            const rUid = r?.user_id?.id ?? r?.user_id;
            return rUid && rUid === uid;
        });
        return found || emptyAccessRule();
    } catch (e) {
        console.warn("[inom_pos_access_management] accessRule lookup failed:", e);
        return emptyAccessRule();
    }
}

const toId = (rec) => rec?.id ?? rec;

patch(PosStore.prototype, {
    get accessRule() {
        return getAccessRule(this.models || this.data?.models);
    },

    async setup() {
        await super.setup(...arguments);
        try {
            this._inom_applyAccessClasses();
            this._inom_removeDebugFromUrl();
        } catch (e) {
            console.warn("[inom_pos_access_management] failed to apply access classes:", e);
        }
    },

    /**
     * Toggle body.o_pos_ar_<flag> classes; the stylesheet hides the matching
     * buttons for as long as the POS is open.
     */
    _inom_applyAccessClasses() {
        const body = document.body;
        if (!body) {
            return;
        }
        const rule = this.accessRule;
        for (const flag of ACCESS_FLAGS) {
            body.classList.toggle("o_pos_ar_" + flag, Boolean(rule[flag]));
        }
    },

    _inom_removeDebugFromUrl() {
        if (!this.accessRule.hide_debug_window) {
            return;
        }
        const url = new URL(window.location.href);
        if (url.searchParams.has("debug")) {
            url.searchParams.delete("debug");
            window.history.replaceState({}, document.title, url.toString());
        }
    },

    // ------------------------------------------------------------------
    // Categories
    // ------------------------------------------------------------------

    /** Ids of the hidden POS categories, including their sub-categories. */
    getInomHiddenCategoryIds() {
        const rule = this.accessRule;
        const hidden = new Set();
        if (!rule.restrict_pos_categories) {
            return hidden;
        }
        const categoryModel = this.models["pos.category"];
        for (const categ of rule.restrict_pos_category_ids || []) {
            const record = categoryModel.get(toId(categ));
            const all = record?.getAllChildren ? record.getAllChildren() : [record];
            for (const c of all) {
                if (c) {
                    hidden.add(c.id);
                }
            }
            hidden.add(toId(categ));
        }
        return hidden;
    },

    isPosCategoryHidden(categoryId) {
        return this.getInomHiddenCategoryIds().has(categoryId);
    },

    /** Also hide products whose POS categories are all hidden. */
    getExcludedProductIds() {
        const excluded = super.getExcludedProductIds(...arguments);
        const hidden = this.getInomHiddenCategoryIds();
        if (!hidden.size) {
            return excluded;
        }
        const productTemplateModel = this.models["product.template"].toRaw();
        const extra = new Set();
        for (const categId of hidden) {
            for (const product of productTemplateModel.getBy("pos_categ_ids", categId) || []) {
                if (product.pos_categ_ids.every((c) => hidden.has(c.id))) {
                    extra.add(product.id);
                }
            }
        }
        return [...excluded, ...extra];
    },

    // ------------------------------------------------------------------
    // Payment methods
    // ------------------------------------------------------------------

    isPaymentMethodAllowed(methodId) {
        const rule = this.accessRule;
        if (!rule.restrict_payment_method) {
            return true;
        }
        const allowed = rule.restrict_payment_method_ids || [];
        return allowed.some((m) => toId(m) === toId(methodId));
    },

    /** Validating without payment lines uses the first config method. */
    getValidationOrderOptions() {
        const opts = super.getValidationOrderOptions(...arguments);
        if (opts.fastPaymentMethod && !this.isPaymentMethodAllowed(opts.fastPaymentMethod)) {
            const allowed = this.config.payment_method_ids
                .slice()
                .sort((a, b) => a.sequence - b.sequence)
                .find((m) => this.isPaymentMethodAllowed(m));
            if (allowed) {
                opts.fastPaymentMethod = allowed;
            } else {
                delete opts.fastPaymentMethod;
            }
        }
        return opts;
    },

    async validateOrderFast(paymentMethod) {
        if (this.accessRule.hide_payment_button || !this.isPaymentMethodAllowed(paymentMethod)) {
            this.notification.add(_t("You are not allowed to use this payment method."), {
                type: "warning",
            });
            return;
        }
        return await super.validateOrderFast(...arguments);
    },
});
