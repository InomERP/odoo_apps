/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";

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
        const rule = this.pos?.accessRule;
        if (!rule?.restrict_pos_categories) return;

        const hiddenIds = (rule.restrict_pos_category_ids || []).map(
            (c) => c?.id ?? c
        );
        if (!hiddenIds.length) return;

        fetch('/web/dataset/call_kw', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                jsonrpc: '2.0',
                method: 'call',
                params: {
                    model: 'pos.category',
                    method: 'search_read',
                    args: [[['id', 'in', hiddenIds]]],
                    kwargs: { fields: ['id', 'name'], limit: 100 }
                }
            })
        })
        .then(r => r.json())
        .then(data => {
            const hiddenNames = (data.result || []).map(
                c => (c.name || "").trim().toLowerCase()
            );

            // CSS inject karo — Owl re-render ke baad bhi kaam karega
            const styleId = "inom_category_hide_style";
            let styleEl = document.getElementById(styleId);
            if (!styleEl) {
                styleEl = document.createElement("style");
                styleEl.id = styleId;
                document.head.appendChild(styleEl);
            }

            // Har hidden category ke liye CSS rule banao
            const rules = hiddenNames.map(name =>
                `button.category-button[data-name="${name}"] { display: none !important; }`
            ).join("\n");
            styleEl.textContent = rules;

            // JS se bhi hide karo (data-name attribute nahi hoga shayad)
            const hideCategories = () => {
                document.querySelectorAll("button.category-button").forEach((btn) => {
                    const text = (btn.textContent || "").trim().toLowerCase();
                    if (hiddenNames.includes(text)) {
                        btn.setAttribute("data-inom-hidden", "true");
                        btn.style.setProperty("display", "none", "important");
                    }
                });
            };

            // Aggressive interval — Owl re-render ke baad bhi kaam kare
            hideCategories();
            const interval = setInterval(hideCategories, 200);
            setTimeout(() => clearInterval(interval), 60000);
        })
        .catch(e => console.warn("[inom] category fetch failed:", e));
    },
});