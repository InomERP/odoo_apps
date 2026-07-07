/** @odoo-module **/

import { Component, useState, useRef, useExternalListener } from "@odoo/owl";
import { widgetStyleStore } from "./widget_style_store";
import { FONTAWESOME_ICONS } from "./fontawesome_icons";

/**
 * InomWidgetMenu
 * ==================================================================
 * One common, reusable three-dot (⋮) menu that can be dropped onto any
 * dashboard widget card (Phase 7.1). It currently exposes:
 *   - "Change Accent Color" - any color via a native color picker (Phase 7.2)
 *   - "Change Icon"         - full Font Awesome 4 icon set, searchable (Phase 7.3)
 *   - "Reset to Default"    - clears the customization for this widget
 *
 * Usage in a template:
 *   <InomWidgetMenu widgetKey="'performers'" defaultIcon="'fa-star'"/>
 *
 * The component is entirely self-contained: it owns its own open/closed
 * state and reads/writes personalization through the shared
 * `widgetStyleStore`, which persists to localStorage and is reactive, so
 * the owning widget updates instantly as soon as a color/icon is chosen -
 * no props drilling or manual events required. It never touches dashboard
 * data, calculations, models, views or any backend call.
 */
export class InomWidgetMenu extends Component {
    static template = "inom_advance_sales_dashboard.WidgetMenu";
    static props = {
        widgetKey: String,
        defaultIcon: { type: String, optional: true },
        defaultColor: { type: String, optional: true },
        chartTypes: { type: Array, optional: true },
        canCsv: { type: Boolean, optional: true },
    };
    static defaultProps = {
        defaultIcon: "fa-square-o",
        defaultColor: "#2563eb",
        chartTypes: [],
        canCsv: false,
    };

    setup() {
        this.store = widgetStyleStore;
        this.rootRef = useRef("menuRoot");
        this.state = useState({ open: false, panel: "root", iconSearch: "" });

        // Every Font Awesome 4 icon class already shipped with Odoo's web
        // assets - not a small curated subset (Phase 7.3 requirement).
        this.icons = FONTAWESOME_ICONS;

        this.chartTypeLabels = {
            line: "Line",
            area: "Area",
            bar: "Bar",
            horizontalBar: "Horizontal Bar",
            doughnut: "Doughnut",
            pie: "Pie",
        };
        this.chartTypeIcons = {
            line: "fa-line-chart",
            area: "fa-area-chart",
            bar: "fa-bar-chart",
            horizontalBar: "fa-tasks",
            doughnut: "fa-pie-chart",
            pie: "fa-pie-chart",
        };

        // Close the dropdown on any outside click.
        useExternalListener(document, "click", (ev) => {
            if (this.state.open && this.rootRef.el && !this.rootRef.el.contains(ev.target)) {
                this.close();
            }
        });
        // Close on Escape for keyboard users.
        useExternalListener(document, "keydown", (ev) => {
            if (this.state.open && ev.key === "Escape") {
                this.close();
            }
        });
    }

    get currentColor() {
        return this.store.getColor(this.props.widgetKey);
    }
    get colorInputValue() {
        // <input type="color"> requires a valid #rrggbb value at all times.
        return this.currentColor || this.props.defaultColor;
    }
    get currentIcon() {
        return this.store.getIcon(this.props.widgetKey) || this.props.defaultIcon;
    }
    get hasCustomStyle() {
        return Boolean(this.store.getColor(this.props.widgetKey) || this.store.getIcon(this.props.widgetKey));
    }
    get isCollapsed() {
        return this.store.isCollapsed(this.props.widgetKey);
    }
    get currentChartType() {
        return this.store.getChartType(this.props.widgetKey) || (this.props.chartTypes[0] || "");
    }
    get hasChartTypes() {
        return this.props.chartTypes && this.props.chartTypes.length > 0;
    }

    // -- Card element that owns this menu (for fullscreen / export) --
    _card() {
        return this.rootRef.el ? this.rootRef.el.closest(".o_inom_gcard") : null;
    }

    // -- Collapse / expand (persisted) --
    toggleCollapse(ev) {
        if (ev) { ev.stopPropagation(); }
        this.store.toggleCollapsed(this.props.widgetKey);
    }

    // -- Full screen (native, per widget) --
    toggleFullscreen(ev) {
        if (ev) { ev.stopPropagation(); }
        const card = this._card();
        if (!card) { return; }
        if (!document.fullscreenElement) {
            if (card.requestFullscreen) { card.requestFullscreen(); }
        } else if (document.exitFullscreen) {
            document.exitFullscreen();
        }
    }

    // -- Chart type (persisted) --
    selectChartType(type) {
        this.store.setChartType(this.props.widgetKey, type);
        this.close();
    }

    // -- Export current widget as PNG --
    async exportPng() {
        this.close();
        const card = this._card();
        const H = window.html2canvas;
        if (!card || !H) { return; }
        card.classList.add("o_inom_capturing");
        try {
            const canvas = await H(card, { backgroundColor: "#ffffff", scale: 2, useCORS: true, logging: false });
            const a = document.createElement("a");
            a.href = canvas.toDataURL("image/png");
            a.download = `widget_${this.props.widgetKey}.png`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
        } catch (error) {
            // best-effort
        } finally {
            card.classList.remove("o_inom_capturing");
        }
    }

    // -- Export ranking/table widget as CSV (scrapes the rendered rows) --
    exportCsv() {
        this.close();
        const card = this._card();
        if (!card) { return; }
        const rows = [];
        const ranked = card.querySelectorAll(".o_inom_ranked__row");
        if (ranked.length) {
            rows.push(["Rank", "Name", "Value"]);
            ranked.forEach((row, i) => {
                const name = (row.querySelector(".o_inom_ranked__name") || {}).textContent || "";
                const value = (row.querySelector(".o_inom_ranked__value") || {}).textContent || "";
                rows.push([i + 1, name.trim(), value.trim()]);
            });
        } else {
            const teams = card.querySelectorAll(".o_inom_team");
            if (teams.length) {
                rows.push(["Team", "Achievement", "Actual", "Target", "Remaining"]);
                teams.forEach((t) => {
                    const name = (t.querySelector(".o_inom_team__name") || {}).textContent || "";
                    const badge = (t.querySelector(".o_inom_badge") || {}).textContent || "";
                    const metrics = t.querySelectorAll(".o_inom_team__metric b");
                    const m = (idx) => (metrics[idx] ? metrics[idx].textContent.trim() : "");
                    rows.push([name.trim(), badge.trim(), m(0), m(1), m(2)]);
                });
            }
        }
        if (rows.length <= 1) { return; }
        const csv = rows.map((r) => r.map((v) => `"${String(v).replace(/"/g, '""')}"`).join(",")).join("\n");
        const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `widget_${this.props.widgetKey}.csv`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }

    get filteredIcons() {
        const term = this.state.iconSearch.trim().toLowerCase();
        if (!term) {
            return this.icons;
        }
        return this.icons.filter((ic) => ic.replace("fa-", "").includes(term));
    }

    toggle(ev) {
        ev.stopPropagation();
        this.state.open = !this.state.open;
        this.state.panel = "root";
    }
    close() {
        this.state.open = false;
        this.state.panel = "root";
    }
    openPanel(panel) {
        this.state.panel = panel;
    }
    backToRoot() {
        this.state.panel = "root";
        this.state.iconSearch = "";
    }
    /** Live-applies and persists the color as the user drags/picks it. */
    onColorInput(ev) {
        this.selectColor(ev.target.value);
    }
    onIconSearchInput(ev) {
        this.state.iconSearch = ev.target.value;
    }
    selectColor(color) {
        this.store.setColor(this.props.widgetKey, color);
    }
    selectIcon(icon) {
        this.store.setIcon(this.props.widgetKey, icon);
    }
    resetStyle(ev) {
        if (ev) { ev.stopPropagation(); }
        this.store.resetWidget(this.props.widgetKey);
        this.close();
    }
}

