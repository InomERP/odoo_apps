import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as PaymentScreen from "@point_of_sale/../tests/pos/tours/utils/payment_screen_util";
import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import { negate } from "@point_of_sale/../tests/generic_helpers/utils";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("InomPosAccessRightsTour", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),

            // Hidden category and its products
            ProductScreen.productIsDisplayed("Desk Pad"),
            {
                content: "hidden category button is not displayed",
                trigger: negate(".category-button:contains('Chair test')"),
            },
            {
                content: "products of the hidden category are not displayed",
                trigger: negate(".product-list .product-name:contains('Letter Tray')"),
            },

            // Numpad: Qty disabled, Price still enabled
            ProductScreen.addOrderline("Desk Pad", "1"),
            {
                content: "Qty numpad button is disabled",
                trigger: ".numpad button.numpad-qty:disabled",
            },
            {
                content: "Price numpad button is enabled",
                trigger: ".numpad button.numpad-price:not(:disabled)",
            },

            // Burger menu: restricted entries hidden, the others still there
            Chrome.clickMenuButton(),
            Chrome.waitForMenuOptionsToOpen(),
            {
                content: "Close Register is hidden",
                trigger: negate(".o_pos_burger_menu_buttons > button.btn:contains('Close Register')"),
            },
            {
                content: "Backend is hidden",
                trigger: negate(".o_pos_burger_menu_buttons > button.btn:contains('Backend')"),
            },
            {
                content: "Cash In/Out is hidden",
                trigger: negate(".o_pos_burger_menu_buttons > button.btn:contains('Cash In/Out')"),
            },
            Chrome.closeBurgerMenu(),

            // Payment methods: only Bank is allowed
            ProductScreen.clickPayButton(),
            PaymentScreen.isShown(),
            {
                content: "Bank payment method is displayed",
                trigger: ".paymentmethods .payment-name:contains('Bank')",
            },
            {
                content: "Cash payment method is not displayed",
                trigger: negate(".paymentmethods .payment-name:contains('Cash')"),
            },
            {
                content: "Invoice button is hidden",
                trigger: ".payment-screen .js_invoice:not(:visible)",
            },
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            Chrome.endTour(),
        ].flat(),
});

registry.category("web_tour.tours").add("InomPosAccessRightsActionsTour", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.addOrderline("Desk Pad", "1"),
            {
                content: "internal Note button is hidden",
                trigger: negate(".control-button:contains('Note')"),
            },
            ProductScreen.clickControlButtonMore(),
            {
                content: "the actions popup is open",
                trigger: ".control-buttons-modal",
            },
            ...["Customer Note", "Pricelist", "Info", "Cancel Order"].map((name) => ({
                content: `${name} button is hidden`,
                trigger: negate(`.control-buttons-modal button:contains('${name}')`),
            })),
            Dialog.cancel(),
            {
                content: "Payment button is hidden",
                trigger: ".product-screen .pay-order-button:not(:visible)",
            },
            Chrome.endTour(),
        ].flat(),
});
