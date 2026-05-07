/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import { rpc } from "@web/core/network/rpc";

/* ------------------------------------------------------------------ *
 * Validate the recharge form on the wallet landing page              *
 * ------------------------------------------------------------------ */
publicWidget.registry.WebsiteWalletRechargeForm = publicWidget.Widget.extend({
    selector: ".o_wallet_recharge_form",
    events: {
        submit: "_onSubmit",
    },

    _onSubmit(ev) {
        const input = this.el.querySelector('input[name="amount"]');
        if (!input) {
            return;
        }
        const value = parseFloat(input.value || "0");
        const min = parseFloat(input.getAttribute("min") || "0");
        const max = parseFloat(input.getAttribute("max") || "0");
        if (isNaN(value) || value < min || (max > 0 && value > max)) {
            ev.preventDefault();
            input.classList.add("is-invalid");
            input.focus();
        }
    },
});

/* ------------------------------------------------------------------ *
 * Inject the "Use Wallet" payment option on the checkout / payment    *
 * page. Uses a JSON RPC call so we don't depend on template-inherit   *
 * xpaths that have changed across Odoo versions.                      *
 *                                                                     *
 * The widget mounts on #wrapwrap (always present on every Odoo        *
 * frontend page when web.assets_frontend is loaded). It then probes   *
 * the DOM repeatedly for a payment-method container -- if one is      *
 * found it inserts the "Use Wallet" card just above it. Retries cope  *
 * with the page rendering its payment form asynchronously.            *
 * ------------------------------------------------------------------ */
publicWidget.registry.WebsiteWalletPaymentOption = publicWidget.Widget.extend({
    selector: "#wrapwrap",

    async start() {
        const _super = this._super.bind(this);
        await _super(...arguments);
        console.log("[website_wallet] payment-option widget started on", window.location.pathname);
        this._injected = false;
        // Try once immediately, then a few times on a short timer to
        // catch payment forms rendered asynchronously by OWL/JS.
        await this._tryInject();
        setTimeout(() => this._tryInject(), 500);
        setTimeout(() => this._tryInject(), 1500);
        setTimeout(() => this._tryInject(), 3500);
    },

    /**
     * Returns the best DOM element to inject the wallet card *before*,
     * or null if this page doesn't appear to be a payment page.
     */
    _findPaymentAnchor() {
        // 1) Known container selectors used across recent Odoo versions
        const containerSelectors = [
            "form#payment_form",
            "form[name='payment_form']",
            "form[name='o_payment_form']",
            "div#payment_method",
            "#o_payment_form",
            "div.o_payment_form",
            "div.o_payment_methods",
            "section#payment",
            "div[id*='payment_method']",
        ];
        for (const sel of containerSelectors) {
            const el = document.querySelector(sel);
            if (el) {
                console.log("[website_wallet] anchor via selector:", sel);
                return el;
            }
        }
        // 2) Walk up from any payment radio input
        const radios = document.querySelectorAll(
            "input[type='radio'][name*='payment'], "
            + "input[type='radio'][name*='provider'], "
            + "input[type='radio'][name='o_payment_radio']"
        );
        if (radios.length) {
            const card = radios[0].closest(
                "form, fieldset, .card, section, div[class*='payment']"
            );
            if (card) {
                console.log("[website_wallet] anchor via payment radio");
                return card;
            }
        }
        // 3) Find a heading that says "Payment method" / "Payment"
        const headings = document.querySelectorAll("h1, h2, h3, h4, h5");
        for (const h of headings) {
            const text = (h.textContent || "").trim().toLowerCase();
            if (text === "payment method" || text === "payment" || text === "payment methods") {
                // Insert AFTER the heading -- so target the next sibling.
                const next = h.nextElementSibling;
                if (next) {
                    console.log("[website_wallet] anchor via heading:", text);
                    return next;
                }
            }
        }
        // 4) Look for "Wire Transfer" label/text -- known to be on
        //    standard manual-payment-method test setups.
        const labels = document.querySelectorAll("label, span, div");
        for (const el of labels) {
            const text = (el.textContent || "").trim().toLowerCase();
            if (text === "wire transfer") {
                const card = el.closest(
                    "form, fieldset, .card, section, div[class*='payment'], div"
                );
                if (card && card !== document.body) {
                    console.log("[website_wallet] anchor via 'Wire Transfer' text");
                    return card;
                }
            }
        }
        return null;
    },

    async _tryInject() {
        if (this._injected) {
            return;
        }
        const anchor = this._findPaymentAnchor();
        if (!anchor) {
            console.log("[website_wallet] no payment anchor found, skipping");
            return;
        }
        let info;
        try {
            info = await rpc("/shop/wallet/info", {});
        } catch (err) {
            console.warn("[website_wallet] /shop/wallet/info failed:", err);
            return;
        }
        if (!info || !info.enabled) {
            console.log("[website_wallet] wallet disabled");
            return;
        }
        if (!info.balance || info.balance <= 0) {
            console.log("[website_wallet] wallet balance is zero, hiding option");
            return;
        }
        if (!info.amount_remaining || info.amount_remaining <= 0) {
            console.log("[website_wallet] nothing left to pay");
            return;
        }
        this._inject(anchor, info);
    },

    _inject(anchor, info) {
        if (document.getElementById("o_wallet_payment_inserted")) {
            this._injected = true;
            return;
        }
        const csrfInput = document.querySelector('input[name="csrf_token"]');
        const csrfToken = (csrfInput && csrfInput.value)
            || (window.odoo && window.odoo.csrf_token)
            || "";

        const card = document.createElement("div");
        card.id = "o_wallet_payment_inserted";
        card.className = "card o_wallet_payment_card border-primary mb-3";
        card.innerHTML = `
            <div class="card-body p-3 d-flex flex-wrap align-items-center justify-content-between gap-2">
                <div class="flex-grow-1">
                    <h6 class="mb-1 d-flex align-items-center">
                        <i class="fa fa-credit-card-alt me-2"></i>
                        <span>Use Wallet</span>
                    </h6>
                    <small class="text-muted">
                        Your Current Wallet Balance is
                        <strong>${escapeHtml(info.balance_formatted)}</strong>
                    </small>
                </div>
                <form action="/shop/wallet/use" method="post" class="m-0">
                    <input type="hidden" name="csrf_token" value="${escapeAttr(csrfToken)}"/>
                    <button type="submit" class="btn btn-primary">
                        <i class="fa fa-money me-1"></i>Use Wallet
                    </button>
                </form>
            </div>
        `;
        if (anchor.parentNode) {
            anchor.parentNode.insertBefore(card, anchor);
        } else {
            anchor.appendChild(card);
        }
        this._injected = true;
        console.log("[website_wallet] Use Wallet option injected");
    },
});

/* ------------------------------------------------------------------ *
 * Tiny HTML-escape helpers                                            *
 * ------------------------------------------------------------------ */
function escapeHtml(s) {
    const div = document.createElement("div");
    div.textContent = s == null ? "" : String(s);
    return div.innerHTML;
}
function escapeAttr(s) {
    return escapeHtml(s).replace(/"/g, "&quot;");
}

export default publicWidget.registry.WebsiteWalletPaymentOption;
