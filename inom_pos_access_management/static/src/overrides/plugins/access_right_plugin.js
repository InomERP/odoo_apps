/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PosAccessRightPlugin } from "@point_of_sale/app/plugins/access_right_plugin";
import { getAccessRule } from "@inom_pos_access_management/overrides/models/pos_store";

/**
 * Plug the user's access rule into Odoo's own POS access-right getters, so
 * the buttons are not rendered (or rendered disabled) by the core templates.
 * Note: for the `disable*` getters, `false` means "disabled" in core.
 */
patch(PosAccessRightPlugin.prototype, {
    get inomRule() {
        return getAccessRule(this.data.models);
    },
    get canCloseSession() {
        return !this.inomRule.hide_close_pos_button && super.canCloseSession;
    },
    get canGoToBackend() {
        return !this.inomRule.hide_backend_pos_button && super.canGoToBackend;
    },
    get canCashMove() {
        return !this.inomRule.hide_cash_in_out_button && super.canCashMove;
    },
    get canAccessDebugMode() {
        return !this.inomRule.hide_debug_window && super.canAccessDebugMode;
    },
    get canInstallApp() {
        return !this.inomRule.hide_debug_window && super.canInstallApp;
    },
    get canAccessPricelist() {
        return !this.inomRule.hide_pricelist_button && super.canAccessPricelist;
    },
    get canAccessFiscalPosition() {
        return !this.inomRule.hide_fiscal_button && super.canAccessFiscalPosition;
    },
    get canAccessQuotation() {
        return !this.inomRule.hide_quotation_button && super.canAccessQuotation;
    },
    get canDeleteOrder() {
        return !this.inomRule.hide_delete_order_button && super.canDeleteOrder;
    },
    get canCancelOrder() {
        return !this.inomRule.hide_delete_order_button && super.canCancelOrder;
    },
    get canEditDetails() {
        return !this.inomRule.hide_save_customer_button && super.canEditDetails;
    },
    get canSwitchSign() {
        return !this.inomRule.disable_plus_minus_button && super.canSwitchSign;
    },
    get disableClickPayment() {
        return !this.inomRule.hide_payment_button && super.disableClickPayment;
    },
    get disableValidateOrder() {
        return !this.inomRule.hide_payment_validate_button && super.disableValidateOrder;
    },
    get disablePartner() {
        return !this.inomRule.hide_customer_button && super.disablePartner;
    },
    get disableLinediscount() {
        return !this.inomRule.disable_discount_button && super.disableLinediscount;
    },
    get disablePriceButton() {
        return !this.inomRule.disable_price_button && super.disablePriceButton;
    },
});
