/** @odoo-module **/

import { reactive } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";

/**
 * Shared, reactive, localStorage-backed store that holds the per-widget
 * personalization (accent color / icon) chosen by the user from the
 * three-dot widget menu (see widget_menu.js).
 *
 * This is a presentation-only concern: nothing here reads or writes any
 * Odoo model, and no backend logic, calculation or report is touched.
 *
 * Because the store is created with owl's `reactive()`, any component that
 * reads from it while rendering (the Dashboard, or any widget menu) is
 * automatically re-rendered whenever a value changes - no manual event
 * wiring or props drilling required. This keeps the three-dot menu a
 * fully self-contained, drop-in component (Phase 7.1).
 */

const STORAGE_KEY = "inom_dashboard_widget_style_v1";

function loadFromStorage() {
    try {
        const raw = browser.localStorage.getItem(STORAGE_KEY);
        if (raw) {
            const parsed = JSON.parse(raw);
            if (parsed && typeof parsed === "object") {
                return parsed;
            }
        }
    } catch (error) {
        // Corrupt or unavailable storage - fall back to defaults.
    }
    return {};
}

function persist(styles) {
    try {
        browser.localStorage.setItem(STORAGE_KEY, JSON.stringify(styles));
    } catch (error) {
        // Storage may be full or disabled (e.g. private browsing) - ignore.
    }
}

export const widgetStyleStore = reactive({
    styles: loadFromStorage(),

    /**
     * @param {string} key widget key (e.g. "performers")
     * @returns {string|undefined} the saved accent color, if any
     */
    getColor(key) {
        return this.styles[key] && this.styles[key].color;
    },
    /**
     * @param {string} key widget key
     * @returns {string|undefined} the saved icon class (e.g. "fa-star"), if any
     */
    getIcon(key) {
        return this.styles[key] && this.styles[key].icon;
    },
    setColor(key, color) {
        this.styles[key] = { ...(this.styles[key] || {}), color };
        persist(this.styles);
    },
    setIcon(key, icon) {
        this.styles[key] = { ...(this.styles[key] || {}), icon };
        persist(this.styles);
    },
    getChartType(key) {
        return this.styles[key] && this.styles[key].chartType;
    },
    setChartType(key, chartType) {
        this.styles[key] = { ...(this.styles[key] || {}), chartType };
        persist(this.styles);
    },
    isCollapsed(key) {
        return Boolean(this.styles[key] && this.styles[key].collapsed);
    },
    setCollapsed(key, collapsed) {
        this.styles[key] = { ...(this.styles[key] || {}), collapsed };
        persist(this.styles);
    },
    toggleCollapsed(key) {
        this.setCollapsed(key, !this.isCollapsed(key));
    },
    resetWidget(key) {
        if (key in this.styles) {
            const next = { ...this.styles };
            delete next[key];
            this.styles = next;
            persist(this.styles);
        }
    },
});
