/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
// Same module path in Odoo 17 and Odoo 18.
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";

/**
 * Hide selected POS categories from the product screen.
 *
 * Odoo-17 migration notes
 * -----------------------
 * Nothing structurally needs to change for Odoo 17: the JSON-RPC
 * endpoint `/web/dataset/call_kw` and the `search_read` call shape are
 * identical to Odoo 18. The `restrict_pos_category_ids` field arrives
 * from the access rule as a raw array of integer ids (Odoo-17
 * `search_read` output) and the `.map(c => c?.id ?? c)` line below
 * happens to be tolerant of both that shape AND the Odoo-18
 * resolved-record shape — so this file is binary-compatible between
 * the two versions.
 */
patch(ProductScreen.prototype, {
    setup() {
        super.setup(...arguments);
        try {
            this._inom_applyCategories();
        } catch (e) {
            console.warn("[inom] category restriction failed:", e);
        }
    },

    _inom_applyCategories() {
        const rule = this.pos && this.pos.accessRule;
        if (!rule || !rule.restrict_pos_categories) return;

        const hiddenIds = (rule.restrict_pos_category_ids || []).map(
            (c) => (Array.isArray(c) ? c[0] : (c && typeof c === "object" ? c.id : c))
        ).filter((x) => x != null);
        if (!hiddenIds.length) return;

        fetch("/web/dataset/call_kw", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                jsonrpc: "2.0",
                method: "call",
                params: {
                    model: "pos.category",
                    method: "search_read",
                    args: [[["id", "in", hiddenIds]]],
                    kwargs: { fields: ["id", "name"], limit: 100 },
                },
            }),
        })
            .then((r) => r.json())
            .then((data) => {
                const hiddenNames = (data.result || []).map(
                    (c) => (c.name || "").trim().toLowerCase()
                );

                // CSS injection — survives OWL re-renders without
                // needing a permanent MutationObserver running.
                const styleId = "inom_category_hide_style";
                let styleEl = document.getElementById(styleId);
                if (!styleEl) {
                    styleEl = document.createElement("style");
                    styleEl.id = styleId;
                    document.head.appendChild(styleEl);
                }

                const rules = hiddenNames
                    .map(
                        (name) =>
                            `button.category-button[data-name="${name}"] { display: none !important; }`
                    )
                    .join("\n");
                styleEl.textContent = rules;

                // Also hide via JS text-matching for categories whose
                // markup doesn't carry a data-name attribute.
                const hideCategories = () => {
                    document
                        .querySelectorAll("button.category-button")
                        .forEach((btn) => {
                            const text = (btn.textContent || "").trim().toLowerCase();
                            if (hiddenNames.includes(text)) {
                                btn.setAttribute("data-inom-hidden", "true");
                                btn.style.setProperty(
                                    "display",
                                    "none",
                                    "important"
                                );
                            }
                        });
                };

                hideCategories();
                const interval = setInterval(hideCategories, 200);
                setTimeout(() => clearInterval(interval), 60000);
            })
            .catch((e) => console.warn("[inom] category fetch failed:", e));
    },
});
