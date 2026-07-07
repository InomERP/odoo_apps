/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { session } from "@web/session";
import { browser } from "@web/core/browser/browser";
import {
    Component,
    onWillStart,
    onMounted,
    onPatched,
    onWillUnmount,
    useState,
    useRef,
} from "@odoo/owl";
import { InomWidgetMenu } from "./widget_menu";
import { widgetStyleStore } from "./widget_style_store";

const LAYOUT_KEY = "inom_dashboard_layout_v1";
const THEME_KEY = "inom_dashboard_theme_v1";

/* ------------------------------------------------------------------ *
 * Color helpers (pure, presentation-only) used to derive lighter and
 * darker shades from a single user-picked accent color, so a widget can
 * be themed completely (border, charts, bars, icon backgrounds, etc.)
 * from one value. No backend, model or data is involved.
 * ------------------------------------------------------------------ */
function inomHexToRgb(hex) {
    const clean = String(hex || "").replace("#", "");
    const full = clean.length === 3 ? clean.split("").map((c) => c + c).join("") : clean;
    const num = parseInt(full || "000000", 16);
    return { r: (num >> 16) & 255, g: (num >> 8) & 255, b: num & 255 };
}
function inomRgbToHex(r, g, b) {
    const to = (v) => Math.round(Math.max(0, Math.min(255, v))).toString(16).padStart(2, "0");
    return "#" + to(r) + to(g) + to(b);
}
/** Mix a color toward white by `amount` (0..1). */
function inomTint(hex, amount) {
    const { r, g, b } = inomHexToRgb(hex);
    return inomRgbToHex(r + (255 - r) * amount, g + (255 - g) * amount, b + (255 - b) * amount);
}
/** Mix a color toward black by `amount` (0..1). */
function inomShade(hex, amount) {
    const { r, g, b } = inomHexToRgb(hex);
    return inomRgbToHex(r * (1 - amount), g * (1 - amount), b * (1 - amount));
}

/**
 * Advanced Sales Dashboard - client action (presentation layer only).
 *
 * Enterprise premium UI: drill-down, KPI growth indicators, animated counters,
 * rich tooltips, skeletons, empty states, premium charts, manual + auto
 * refresh, full screen, personalization (show/hide + reorder + localStorage),
 * top performer cards, comparison cards, alert panel, target widget and export
 * (PDF / Excel / CSV / Image).
 *
 * No existing calculation, report, model, security, menu or database structure
 * is modified. Backend is not changed in this phase (alerts use read-only
 * search counts on existing models; comparisons reuse the existing method).
 */
export class InomSalesDashboard extends Component {
    static components = { InomWidgetMenu };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.rootRef = useRef("root");
        this.state = useState({
            loading: true,
            data: null,
            enterprise: null,
            prevData: null,
            alerts: [],
            lastUpdated: "",
            preset: "all",
            dateFrom: "",
            dateTo: "",
            filters: { salesperson: false, team: false, category: false, customer: false, company: false },
            options: { salespersons: [], teams: [], categories: [], customers: [], companies: [] },
            refreshMode: "manual",
            exportOpen: false,
            customizeOpen: false,
            layout: this._loadLayout(),
            theme: this._loadTheme(),
        });
        this._charts = [];
        this._refreshTimer = null;
        this._dragKey = null;
        this._palette = [
            "#2563eb", "#16a34a", "#7c3aed", "#ea580c", "#0ea5e9",
            "#db2777", "#14b8a6", "#f59e0b", "#6366f1", "#64748b",
        ];
        this._widgetLabels = {
            performers: "Top Performers",
            comparison: "Period Comparison",
            alerts: "Alerts",
            monthly: "Monthly Revenue Trend",
            products_rev: "Top Products by Revenue",
            products_vol: "Top Products by Volume",
            category: "Revenue by Category",
            salesperson: "Sales by Salesperson",
            country: "Sales by Country",
            target: "Revenue Target Achievement",
            customers: "Top Customers",
            funnel: "Sales Funnel",
            leaderboard: "Salesperson Performance",
            product_analytics: "Product Performance",
            target_achievement: "Target vs Achievement",
        };

        this._onFsChange = () => {
            setTimeout(() => {
                this._charts.forEach((c) => { try { c.resize(); } catch (e) { /* ignore */ } });
            }, 60);
        };

        onWillStart(async () => {
            await this._loadFilterOptions();
            await this._loadData();
        });
        onMounted(() => {
            this._afterRender();
            document.addEventListener("fullscreenchange", this._onFsChange);
        });
        onPatched(() => this._afterRender());
        onWillUnmount(() => {
            document.removeEventListener("fullscreenchange", this._onFsChange);
            this._destroyCharts();
            if (this._refreshTimer) {
                clearInterval(this._refreshTimer);
            }
        });
    }

    _afterRender() {
        this._renderCharts();
        this._animateCountUp();
    }

    // ==================================================================
    // Personalization (layout in localStorage)
    // ==================================================================
    _defaultLayout() {
        return [
            { key: "performers", visible: true },
            { key: "comparison", visible: true },
            { key: "alerts", visible: true },
            { key: "monthly", visible: true },
            { key: "products_rev", visible: true },
            { key: "products_vol", visible: true },
            { key: "category", visible: true },
            { key: "salesperson", visible: true },
            { key: "country", visible: true },
            { key: "target", visible: true },
            { key: "customers", visible: true },
            { key: "funnel", visible: true },
            { key: "leaderboard", visible: true },
            { key: "product_analytics", visible: true },
            { key: "target_achievement", visible: true },
        ];
    }
    _loadLayout() {
        try {
            const raw = browser.localStorage.getItem(LAYOUT_KEY);
            if (raw) {
                const saved = JSON.parse(raw);
                const def = this._defaultLayout();
                const known = new Set(def.map((d) => d.key));
                const merged = saved.filter((s) => known.has(s.key));
                const seen = new Set(merged.map((s) => s.key));
                def.forEach((d) => { if (!seen.has(d.key)) { merged.push(d); } });
                return merged;
            }
        } catch (error) {
            // Ignore and use default.
        }
        return this._defaultLayout();
    }
    _saveLayout() {
        try {
            browser.localStorage.setItem(LAYOUT_KEY, JSON.stringify(this.state.layout));
        } catch (error) {
            // Ignore storage errors.
        }
    }
    widgetLabel(key) {
        return this._widgetLabels[key] || key;
    }

    // ==================================================================
    // Light / Dark theme (visual only, scoped to this dashboard)
    // ==================================================================
    _loadTheme() {
        try {
            const saved = browser.localStorage.getItem(THEME_KEY);
            if (saved === "dark" || saved === "light") { return saved; }
        } catch (error) {
            // Ignore and use default.
        }
        return "light";
    }
    _saveTheme() {
        try {
            browser.localStorage.setItem(THEME_KEY, this.state.theme);
        } catch (error) {
            // Ignore storage errors.
        }
    }
    toggleTheme() {
        this.state.theme = this.state.theme === "dark" ? "light" : "dark";
        this._saveTheme();
        // Charts are canvas-based (not CSS), so re-render them with the
        // new theme's colors. Data/labels/calculations are untouched.
        this._renderCharts();
    }
    get isDark() {
        return this.state.theme === "dark";
    }

    // ==================================================================
    // Per-widget personalization (accent color / icon) - Phase 7.2 / 7.3
    // Read-only helpers used by the template; all writes happen inside
    // the reusable <InomWidgetMenu/> component via widgetStyleStore.
    // ==================================================================
    widgetIcon(key, fallback) {
        return widgetStyleStore.getIcon(key) || fallback;
    }
    widgetAccentStyle(key) {
        const color = widgetStyleStore.getColor(key);
        if (!color) {
            return "";
        }
        // Derive lighter/darker shades once, from the single picked color.
        const gradLight = inomTint(color, 0.35);
        const soft = inomTint(color, 0.55);
        const bg = inomTint(color, 0.80);
        const dark = inomShade(color, 0.12);
        return [
            `--inom-accent:${color}`,
            `--inom-accent-light:${gradLight}`,
            `--inom-accent-soft:${soft}`,
            `--inom-accent-bg:${bg}`,
            `--inom-accent-dark:${dark}`,
        ].join(";") + ";";
    }
    /** Accent color for a widget's charts, with a per-widget fallback. */
    _accent(key, fallback) {
        return widgetStyleStore.getColor(key) || fallback;
    }
    /** Build `n` distinguishable monochromatic shades from one accent color. */
    _shades(hex, n) {
        const out = [];
        const count = Math.max(1, n);
        for (let i = 0; i < count; i++) {
            const amount = count === 1 ? 0 : (i * 0.6) / (count - 1);
            out.push(inomTint(hex, amount));
        }
        return out;
    }
    widgetCardClass(key) {
        const classes = [];
        if (widgetStyleStore.getColor(key)) { classes.push("has-accent"); }
        if (widgetStyleStore.isCollapsed(key)) { classes.push("is-collapsed"); }
        return classes.join(" ");
    }
    widgetChartType(key) {
        // Read in the template so a chart-type change re-renders the dashboard,
        // which re-runs _renderCharts with the newly chosen type.
        return widgetStyleStore.getChartType(key) || "";
    }
    isVisible(key) {
        const w = this.state.layout.find((x) => x.key === key);
        return w ? w.visible : true;
    }
    sizeClass(key) {
        if (["performers", "comparison", "alerts", "monthly", "funnel", "leaderboard", "product_analytics", "target_achievement"].includes(key)) { return "w-full"; }
        if (["products_rev", "products_vol", "category"].includes(key)) { return "w-third"; }
        return "w-half";
    }
    toggleWidget(key) {
        const w = this.state.layout.find((x) => x.key === key);
        if (w) { w.visible = !w.visible; this._saveLayout(); }
    }
    toggleCustomize() {
        this.state.customizeOpen = !this.state.customizeOpen;
    }
    resetLayout() {
        this.state.layout = this._defaultLayout();
        this._saveLayout();
    }
    onDragStart(key) {
        this._dragKey = key;
    }
    onDragOver(ev) {
        ev.preventDefault();
    }
    onDrop(key) {
        if (!this._dragKey || this._dragKey === key) { this._dragKey = null; return; }
        const arr = [...this.state.layout];
        const from = arr.findIndex((w) => w.key === this._dragKey);
        const to = arr.findIndex((w) => w.key === key);
        if (from === -1 || to === -1) { this._dragKey = null; return; }
        const [moved] = arr.splice(from, 1);
        arr.splice(to, 0, moved);
        this.state.layout = arr;
        this._saveLayout();
        this._dragKey = null;
    }

    // ==================================================================
    // Data loading
    // ==================================================================
    async _loadFilterOptions() {
        try {
            const [users, teams, cats, partners, companies] = await Promise.all([
                this.orm.searchRead("res.users", [["share", "=", false]], ["name"], { limit: 100, order: "name" }),
                this.orm.searchRead("crm.team", [], ["name"], { limit: 100, order: "name" }),
                this.orm.searchRead("product.category", [], ["display_name"], { limit: 200, order: "complete_name" }),
                this.orm.searchRead("res.partner", [["customer_rank", ">", 0]], ["name"], { limit: 200, order: "name" }),
                this.orm.searchRead("res.company", [], ["name"], { limit: 50, order: "name" }),
            ]);
            this.state.options = { salespersons: users, teams, categories: cats, customers: partners, companies };
        } catch (error) {
            // Options remain empty on failure.
        }
    }

    _buildFilters() {
        const f = this.state.filters;
        const out = {};
        if (f.salesperson) { out.salesperson_ids = [f.salesperson]; }
        if (f.team) { out.team_ids = [f.team]; }
        if (f.category) { out.category_ids = [f.category]; }
        if (f.customer) { out.partner_ids = [f.customer]; }
        if (f.company) { out.company_ids = [f.company]; }
        return out;
    }

    async _loadData() {
        this.state.loading = true;
        const range = this._effectiveRange();
        const filters = this._buildFilters();
        this.state.data = await this.orm.call("sale.dashboard", "get_dashboard_data", [], {
            date_from: range.date_from || false,
            date_to: range.date_to || false,
            filters: filters,
        });
        const prev = this._previousRange();
        if (prev) {
            this.state.prevData = await this.orm.call("sale.dashboard", "get_dashboard_data", [], {
                date_from: prev.date_from, date_to: prev.date_to, filters: filters,
            });
        } else {
            this.state.prevData = null;
        }
        this.state.enterprise = await this.orm.call("sale.dashboard", "get_enterprise_data", [], {
            date_from: range.date_from || false,
            date_to: range.date_to || false,
            filters: filters,
        });
        await this._loadAlerts();
        this.state.lastUpdated = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
        this.state.loading = false;
    }

    async _loadAlerts() {
        const alerts = [];
        const teams = (this.state.data && this.state.data.sales_by_team) || [];
        const missed = teams.filter((t) => t.has_target && Number(t.achievement_pct || 0) < 100).length;
        if (missed) {
            alerts.push({ icon: "fa-bullseye", level: "danger", label: `${missed} sales team(s) below revenue target` });
        }
        const companyLeaf = this.state.filters.company ? [["company_id", "=", this.state.filters.company]] : [];
        try {
            const quotations = await this.orm.searchCount("sale.order", [["state", "in", ["draft", "sent"]], ...companyLeaf]);
            if (quotations) {
                alerts.push({ icon: "fa-file-text-o", level: "warning", label: `${quotations} pending quotation(s)` });
            }
            const sent = await this.orm.searchCount("sale.order", [["state", "=", "sent"], ...companyLeaf]);
            if (sent) {
                alerts.push({ icon: "fa-clock-o", level: "warning", label: `${sent} quotation(s) awaiting confirmation` });
            }
            const now = new Date().toISOString().slice(0, 19).replace("T", " ");
            const late = await this.orm.searchCount("stock.picking", [
                ["state", "not in", ["done", "cancel"]],
                ["scheduled_date", "<", now],
                ["picking_type_id.code", "=", "outgoing"],
                ...companyLeaf,
            ]);
            if (late) {
                alerts.push({ icon: "fa-truck", level: "danger", label: `${late} late delivery(ies)` });
            }
        } catch (error) {
            // Alert counts are best-effort.
        }
        this.state.alerts = alerts;
    }

    // ==================================================================
    // Header info
    // ==================================================================
    get companyName() {
        try {
            const uc = session && session.user_companies;
            if (uc && uc.allowed_companies) {
                let id = uc.current_company;
                if (id && typeof id === "object") { id = id.id; }
                const company = uc.allowed_companies[id];
                if (company && company.name) { return company.name; }
            }
        } catch (error) { /* ignore */ }
        return "";
    }
    get lastUpdated() { return this.state.lastUpdated || "-"; }
    get periodLabel() {
        const labels = { all: "All Time", month: "This Month", quarter: "This Quarter", year: "This Year" };
        if (this.state.preset === "custom") { return `${this.state.dateFrom || "..."} to ${this.state.dateTo || "..."}`; }
        return labels[this.state.preset] || "All Time";
    }

    // ==================================================================
    // Period ranges
    // ==================================================================
    _pad(value) { return String(value).padStart(2, "0"); }
    _fmtDate(d) { return `${d.getFullYear()}-${this._pad(d.getMonth() + 1)}-${this._pad(d.getDate())}`; }
    _effectiveRange() {
        const p = this.state.preset;
        const now = new Date();
        const y = now.getFullYear();
        const m = now.getMonth();
        const r = (s, e) => ({ date_from: `${this._fmtDate(s)} 00:00:00`, date_to: `${this._fmtDate(e)} 23:59:59` });
        if (p === "month") { return r(new Date(y, m, 1), new Date(y, m + 1, 0)); }
        if (p === "quarter") { const q = Math.floor(m / 3); return r(new Date(y, q * 3, 1), new Date(y, q * 3 + 3, 0)); }
        if (p === "year") { return r(new Date(y, 0, 1), new Date(y, 11, 31)); }
        if (p === "custom") {
            return {
                date_from: this.state.dateFrom ? `${this.state.dateFrom} 00:00:00` : false,
                date_to: this.state.dateTo ? `${this.state.dateTo} 23:59:59` : false,
            };
        }
        return { date_from: false, date_to: false };
    }
    _previousRange() {
        const p = this.state.preset;
        const now = new Date();
        const y = now.getFullYear();
        const m = now.getMonth();
        const r = (s, e) => ({ date_from: `${this._fmtDate(s)} 00:00:00`, date_to: `${this._fmtDate(e)} 23:59:59` });
        if (p === "month") { return r(new Date(y, m - 1, 1), new Date(y, m, 0)); }
        if (p === "quarter") { const q = Math.floor(m / 3); return r(new Date(y, (q - 1) * 3, 1), new Date(y, (q - 1) * 3 + 3, 0)); }
        if (p === "year") { return r(new Date(y - 1, 0, 1), new Date(y - 1, 11, 31)); }
        if (p === "custom") {
            if (!this.state.dateFrom || !this.state.dateTo) { return null; }
            const s = new Date(this.state.dateFrom);
            const e = new Date(this.state.dateTo);
            const days = Math.round((e - s) / 86400000) + 1;
            const pe = new Date(s); pe.setDate(pe.getDate() - 1);
            const ps = new Date(pe); ps.setDate(ps.getDate() - days + 1);
            return r(ps, pe);
        }
        return null;
    }

    // ==================================================================
    // Handlers: filters / refresh / fullscreen / export
    // ==================================================================
    async _applyAndReload() { await this._loadData(); }
    async onPresetChange(ev) {
        this.state.preset = ev.target.value;
        if (this.state.preset !== "custom") { await this._applyAndReload(); }
    }
    async onDateFromChange(ev) { this.state.dateFrom = ev.target.value; if (this.state.preset === "custom") { await this._applyAndReload(); } }
    async onDateToChange(ev) { this.state.dateTo = ev.target.value; if (this.state.preset === "custom") { await this._applyAndReload(); } }
    async onFilterChange(dim, ev) {
        const v = ev.target.value;
        this.state.filters[dim] = v ? parseInt(v, 10) : false;
        await this._applyAndReload();
    }
    async manualRefresh() { await this._loadData(); }
    onRefreshChange(ev) { this.state.refreshMode = ev.target.value; this._setupRefresh(); }
    _setupRefresh() {
        if (this._refreshTimer) { clearInterval(this._refreshTimer); this._refreshTimer = null; }
        const map = { "30": 30000, "60": 60000, "300": 300000 };
        const ms = map[this.state.refreshMode];
        if (ms) { this._refreshTimer = setInterval(() => this._loadData(), ms); }
    }
    toggleFullscreen() {
        const el = this.rootRef.el;
        if (!el) { return; }
        if (!document.fullscreenElement) {
            if (el.requestFullscreen) { el.requestFullscreen(); }
        } else if (document.exitFullscreen) {
            document.exitFullscreen();
        }
    }

    toggleExport() { this.state.exportOpen = !this.state.exportOpen; }
    _exportRows() {
        const d = this.state.data || {};
        const rows = [];
        const push = (s, l, v) => rows.push([s, l, v]);
        if (d.summary) { push("KPI", "Total Revenue", d.summary.total_revenue); push("KPI", "Total Sale Orders", d.summary.total_orders); }
        push("KPI", "% Orders from New Customers", d.orders_from_new_pct);
        push("KPI", "% Orders from Repeat Customers", d.orders_from_repeat_pct);
        (d.monthly_revenue || []).forEach((m) => push("Monthly Revenue", m.period, m.revenue));
        (d.top_products_revenue || []).forEach((p) => push("Top Product by Revenue", p.product_name, p.revenue));
        (d.top_products_volume || []).forEach((p) => push("Top Product by Volume", p.product_name, p.quantity));
        (d.revenue_by_category || []).forEach((c) => push("Revenue by Category", c.category_name, c.revenue));
        (d.sales_by_salesperson || []).forEach((s) => push("Sales by Salesperson", s.salesperson, s.revenue));
        (d.sales_by_country || []).forEach((c) => push("Sales by Country", c.country, c.revenue));
        (d.sales_by_team || []).forEach((t) => push("Team Achievement %", t.team, t.achievement_pct));
        (d.top_customers || []).forEach((c) => push("Top Customer by Revenue", c.customer, c.revenue));
        return rows;
    }
    _download(name, mime, content) {
        const blob = new Blob([content], { type: mime });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url; a.download = name;
        document.body.appendChild(a); a.click(); document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }
    exportCSV() {
        const rows = [["Section", "Label", "Value"], ...this._exportRows()];
        const csv = rows.map((r) => r.map((v) => `"${String(v === undefined || v === null ? "" : v).replace(/"/g, '""')}"`).join(",")).join("\n");
        this._download("sales_dashboard.csv", "text/csv;charset=utf-8;", csv);
        this.state.exportOpen = false;
    }
    exportExcel() {
        const rows = [["Section", "Label", "Value"], ...this._exportRows()];
        let html = "<table border='1'><tr>" + rows[0].map((h) => `<th>${h}</th>`).join("") + "</tr>";
        rows.slice(1).forEach((r) => { html += "<tr>" + r.map((c) => `<td>${c === undefined || c === null ? "" : c}</td>`).join("") + "</tr>"; });
        html += "</table>";
        this._download("sales_dashboard.xls", "application/vnd.ms-excel;charset=utf-8;", `<html><head><meta charset="utf-8"/></head><body>${html}</body></html>`);
        this.state.exportOpen = false;
    }
    exportPDF() { this.state.exportOpen = false; window.print(); }
    async exportImage() {
        this.state.exportOpen = false;
        const H = window.html2canvas;
        if (!H || !this.rootRef.el) { return; }
        try {
            const canvas = await H(this.rootRef.el, { backgroundColor: "#f3f5f9", scale: 1.5, useCORS: true, logging: false });
            const a = document.createElement("a");
            a.href = canvas.toDataURL("image/png");
            a.download = "sales_dashboard.png";
            document.body.appendChild(a); a.click(); document.body.removeChild(a);
        } catch (error) {
            // Image export is best-effort.
        }
    }

    // ==================================================================
    // KPI trend indicators + comparison + top performers
    // ==================================================================
    _trendValue(cur, prev) {
        if (prev === null || prev === undefined || prev === 0) { return null; }
        const pct = ((Number(cur || 0) - Number(prev)) / Number(prev)) * 100;
        return { pct: Math.abs(pct).toFixed(1), dir: pct >= 0 ? "up" : "down" };
    }
    get revenueTrend() { return this.state.prevData ? this._trendValue(this.state.data.summary.total_revenue, this.state.prevData.summary.total_revenue) : null; }
    get ordersTrend() { return this.state.prevData ? this._trendValue(this.state.data.summary.total_orders, this.state.prevData.summary.total_orders) : null; }
    get newCustTrend() { return this.state.prevData ? this._trendValue(this.state.data.customer_mix.new_customers, this.state.prevData.customer_mix.new_customers) : null; }
    get repeatCustTrend() { return this.state.prevData ? this._trendValue(this.state.data.customer_mix.repeat_customers, this.state.prevData.customer_mix.repeat_customers) : null; }

    get comparison() {
        if (!this.state.prevData) { return null; }
        const cur = this.state.data.summary || {};
        const prev = this.state.prevData.summary || {};
        const g = (c, p) => (p ? (((c - p) / p) * 100) : null);
        return {
            curRevenue: cur.total_revenue || 0,
            prevRevenue: prev.total_revenue || 0,
            revDiff: (cur.total_revenue || 0) - (prev.total_revenue || 0),
            revGrowth: g(cur.total_revenue || 0, prev.total_revenue || 0),
            curOrders: cur.total_orders || 0,
            prevOrders: prev.total_orders || 0,
            ordDiff: (cur.total_orders || 0) - (prev.total_orders || 0),
            ordGrowth: g(cur.total_orders || 0, prev.total_orders || 0),
        };
    }
    get bestSalesperson() { const l = (this.state.data && this.state.data.sales_by_salesperson) || []; return l.length ? l[0] : null; }
    get topCustomer() { const l = (this.state.data && this.state.data.top_customers) || []; return l.length ? l[0] : null; }
    get bestProduct() { const l = (this.state.data && this.state.data.top_products_volume) || []; return l.length ? l[0] : null; }
    get topCategory() { const l = (this.state.data && this.state.data.revenue_by_category) || []; return l.length ? l[0] : null; }

    // ==================================================================
    // Formatting
    // ==================================================================
    formatAmount(value) {
        const symbol = (this.state.data && this.state.data.currency && this.state.data.currency.symbol) || "";
        const num = Number(value || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
        return symbol ? `${symbol} ${num}` : num;
    }
    formatPercent(value) { return `${Number(value || 0).toFixed(2)}%`; }
    formatQuantity(value) { return Number(value || 0).toLocaleString(undefined, { maximumFractionDigits: 2 }); }
    formatSignedPercent(value) {
        if (value === null || value === undefined) { return "-"; }
        const v = Number(value);
        return (v >= 0 ? "+" : "") + v.toFixed(1) + "%";
    }

    // ==================================================================
    // W-11 helpers
    // ==================================================================
    achievementClass(pct, hasTarget) {
        if (!hasTarget) { return "is-none"; }
        const v = Number(pct || 0);
        if (v > 100) { return "is-darkgreen"; }
        if (v >= 80) { return "is-green"; }
        if (v >= 50) { return "is-yellow"; }
        return "is-red";
    }
    remaining(team) { return Math.max(Number(team.target_amount || 0) - Number(team.actual_revenue || 0), 0); }
    barWidth(value, maxValue) {
        const max = Number(maxValue || 0);
        if (!max) { return 0; }
        return Math.max(0, Math.min(100, (Number(value || 0) / max) * 100));
    }
    _maxOf(list, key) {
        if (!list || !list.length) { return 0; }
        return list.reduce((acc, item) => Math.max(acc, Number(item[key] || 0)), 0);
    }
    get maxProductRevenue() { return this._maxOf(this.state.data.top_products_revenue, "revenue"); }
    get maxProductVolume() { return this._maxOf(this.state.data.top_products_volume, "quantity"); }
    get maxCustomerRevenue() { return this._maxOf(this.state.data.top_customers, "revenue"); }

    // ==================================================================
    // Drill-down
    // ==================================================================
    _advOrderLeaves() {
        const f = this.state.filters;
        const d = [];
        if (f.salesperson) { d.push(["user_id", "=", f.salesperson]); }
        if (f.team) { d.push(["team_id", "=", f.team]); }
        if (f.customer) { d.push(["partner_id", "=", f.customer]); }
        if (f.company) { d.push(["company_id", "=", f.company]); }
        if (f.category) { d.push(["order_line.product_id.categ_id", "=", f.category]); }
        return d;
    }
    _advLineLeaves() {
        const f = this.state.filters;
        const d = [];
        if (f.salesperson) { d.push(["order_id.user_id", "=", f.salesperson]); }
        if (f.team) { d.push(["order_id.team_id", "=", f.team]); }
        if (f.customer) { d.push(["order_id.partner_id", "=", f.customer]); }
        if (f.company) { d.push(["order_id.company_id", "=", f.company]); }
        if (f.category) { d.push(["product_id.categ_id", "=", f.category]); }
        return d;
    }
    _periodOrderLeaves() {
        const r = this._effectiveRange();
        const d = [];
        if (r.date_from) { d.push(["date_order", ">=", r.date_from]); }
        if (r.date_to) { d.push(["date_order", "<=", r.date_to]); }
        return d;
    }
    _periodLineLeaves() {
        const r = this._effectiveRange();
        const d = [];
        if (r.date_from) { d.push(["order_id.date_order", ">=", r.date_from]); }
        if (r.date_to) { d.push(["order_id.date_order", "<=", r.date_to]); }
        return d;
    }
    _orderBase() { return [["state", "in", ["sale", "done"]], ...this._periodOrderLeaves(), ...this._advOrderLeaves()]; }
    _lineBase() { return [["order_id.state", "in", ["sale", "done"]], ["product_id", "!=", false], ...this._periodLineLeaves(), ...this._advLineLeaves()]; }
    _open(name, resModel, domain, viewMode = "list,form") {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: name,
            res_model: resModel,
            domain: domain,
            view_mode: viewMode,
            views: viewMode.split(",").map((m) => [false, m]),
            target: "current",
        });
    }
    openTotalRevenue() { this._open("Confirmed Sale Orders", "sale.order", this._orderBase()); }
    openTotalOrders() { this._open("Sale Orders", "sale.order", this._orderBase()); }
    openNewRepeat() { this._open("Orders (Selected Period)", "sale.order", this._orderBase()); }
    openMonth(index) {
        const m = (this.state.data.monthly_revenue || [])[index];
        if (!m) { return; }
        const domain = [["state", "in", ["sale", "done"]], ...this._advOrderLeaves()];
        const parsed = new Date(`${m.period} 1`);
        if (!isNaN(parsed.getTime())) {
            const s = new Date(parsed.getFullYear(), parsed.getMonth(), 1);
            const e = new Date(parsed.getFullYear(), parsed.getMonth() + 1, 1);
            domain.push(["date_order", ">=", `${this._fmtDate(s)} 00:00:00`]);
            domain.push(["date_order", "<", `${this._fmtDate(e)} 00:00:00`]);
        } else {
            domain.push(...this._periodOrderLeaves());
        }
        this._open(`Orders - ${m.period}`, "sale.order", domain);
    }
    openCategory(index) {
        const c = (this.state.data.revenue_by_category || [])[index];
        if (!c) { return; }
        const domain = [...this._lineBase()];
        if (c.category_id) { domain.push(["product_id.categ_id", "=", c.category_id]); }
        this._open(`Sales - ${c.category_name}`, "sale.order.line", domain);
    }
    openSalesperson(index) {
        const s = (this.state.data.sales_by_salesperson || [])[index];
        if (!s) { return; }
        const domain = [...this._orderBase(), ["user_id", "=", s.user_id || false]];
        this._open(`Orders - ${s.salesperson}`, "sale.order", domain);
    }
    openCountry(index) {
        const c = (this.state.data.sales_by_country || [])[index];
        if (!c) { return; }
        const domain = [...this._orderBase(), ["partner_id.country_id", "=", c.country_id || false]];
        this._open(`Orders - ${c.country}`, "sale.order", domain);
    }
    openProduct(item) { this._open(`Sales - ${item.product_name}`, "sale.order.line", [...this._lineBase(), ["product_id", "=", item.product_id]]); }
    openCustomer(item) { this._open(`Orders - ${item.customer}`, "sale.order", [...this._orderBase(), ["partner_id", "=", item.partner_id]]); }
    openTeam(item) {
        const domain = [];
        if (item.team_id) { domain.push(["team_id", "=", item.team_id]); }
        this._open("Sales Revenue Targets", "inom.sales.target", domain);
    }

    // -- Enterprise widget helpers --
    get funnel() { return (this.state.enterprise && this.state.enterprise.funnel) || []; }
    get leaderboard() { return (this.state.enterprise && this.state.enterprise.leaderboard) || []; }
    get productAnalytics() { return (this.state.enterprise && this.state.enterprise.products) || null; }
    get targetAchievement() { return (this.state.enterprise && this.state.enterprise.target_achievement) || null; }

    leaderClass(row) {
        if (!row.has_target) { return "is-none"; }
        const v = Number(row.achievement || 0);
        if (v >= 100) { return "is-green"; }
        if (v >= 80) { return "is-yellow"; }
        return "is-red";
    }
    funnelIcon(key) {
        const map = {
            quotation: "fa-file-text-o",
            sale_order: "fa-shopping-cart",
            delivery: "fa-truck",
            invoice: "fa-file-text",
            payment: "fa-credit-card",
        };
        return map[key] || "fa-circle-o";
    }
    medal(rank) {
        return { 1: "\uD83E\uDD47", 2: "\uD83E\uDD48", 3: "\uD83E\uDD49" }[rank] || "";
    }

    _companyLeaf() {
        return this.state.filters.company ? [["company_id", "=", this.state.filters.company]] : [];
    }

    openFunnelStage(stage) {
        const key = stage && stage.key;
        if (key === "quotation") {
            this._open("Quotations", "sale.order", [["state", "!=", "cancel"], ...this._periodOrderLeaves(), ...this._advOrderLeaves()]);
        } else if (key === "sale_order") {
            this._open("Sales Orders", "sale.order", this._orderBase());
        } else if (key === "delivery") {
            this._open("Deliveries", "stock.picking", [["picking_type_id.code", "=", "outgoing"], ["state", "=", "done"], ...this._companyLeaf()]);
        } else if (key === "invoice") {
            this._open("Invoiced Orders", "sale.order", [...this._orderBase(), ["invoice_status", "=", "invoiced"]]);
        } else if (key === "payment") {
            const d = [["move_type", "=", "out_invoice"], ["state", "=", "posted"], ["payment_state", "in", ["paid", "in_payment"]], ...this._companyLeaf()];
            const r = this._effectiveRange();
            if (r.date_from) { d.push(["invoice_date", ">=", r.date_from]); }
            if (r.date_to) { d.push(["invoice_date", "<=", r.date_to]); }
            this._open("Paid Invoices", "account.move", d);
        }
    }
    openLeaderboardRow(row) {
        this._open(`Orders - ${row.salesperson}`, "sale.order", [...this._orderBase(), ["user_id", "=", row.user_id || false]]);
    }
    openTargetRecords() {
        this._open("Sales Revenue Targets", "inom.sales.target", this._companyLeaf());
    }

    // ==================================================================
    // Count-up animation
    // ==================================================================
    _animateCountUp() {
        if (!this.rootRef.el || this.state.loading) { return; }
        const nodes = this.rootRef.el.querySelectorAll("[data-countup]");
        nodes.forEach((node) => {
            const target = parseFloat(node.getAttribute("data-value")) || 0;
            const type = node.getAttribute("data-format");
            const duration = 700;
            const start = performance.now();
            const render = (value) => {
                if (type === "amount") { node.textContent = this.formatAmount(value); }
                else if (type === "percent") { node.textContent = this.formatPercent(value); }
                else { node.textContent = Math.round(value).toLocaleString(); }
            };
            const step = (now) => {
                const p = Math.min(1, (now - start) / duration);
                const eased = 0.5 - Math.cos(p * Math.PI) / 2;
                render(target * eased);
                if (p < 1) { requestAnimationFrame(step); } else { render(target); }
            };
            render(0);
            requestAnimationFrame(step);
        });
    }

    // ==================================================================
    // Charts
    // ==================================================================
    _color(index) { return this._palette[index % this._palette.length]; }
    _gradient(canvas, hex) {
        const c = canvas.getContext("2d");
        const g = c.createLinearGradient(0, 0, 0, canvas.height || 260);
        g.addColorStop(0, hex + "59");
        g.addColorStop(1, hex + "05");
        return g;
    }
    _animation() { return { duration: 800, easing: "easeOutQuart" }; }
    /* Theme-aware chart colors (colors only - never touches chart data). */
    _gridColor() { return this.isDark ? "rgba(255,255,255,.08)" : "#eef2f7"; }
    _tickColor() { return this.isDark ? "#9aa7bd" : "#6b7280"; }
    _legendColor() { return this.isDark ? "#e7ebf3" : "#33465e"; }
    _sliceBorderColor() { return this.isDark ? "#151c2c" : "#fff"; }
    _amountTooltip() {
        const self = this;
        return {
            padding: 10,
            callbacks: {
                label(ctx) {
                    const v = ctx.parsed && ctx.parsed.y !== undefined ? ctx.parsed.y : ctx.parsed;
                    return "  Revenue: " + self.formatAmount(v);
                },
            },
        };
    }
    _plainBarOptions() {
        return {
            responsive: true, maintainAspectRatio: false, animation: this._animation(),
            plugins: {
                legend: { display: false },
                tooltip: {
                    padding: 10,
                    callbacks: {
                        label(ctx) {
                            const v = ctx.parsed && ctx.parsed.y !== undefined ? ctx.parsed.y : ctx.parsed;
                            return "  " + (ctx.dataset.label || "") + ": " + v;
                        },
                    },
                },
            },
            scales: {
                x: { grid: { display: false }, ticks: { font: { size: 11 }, color: this._tickColor() } },
                y: { grid: { color: this._gridColor() }, ticks: { font: { size: 11 }, color: this._tickColor() }, beginAtZero: true },
            },
        };
    }
    _barOptions(onClick) {
        return {
            responsive: true, maintainAspectRatio: false, animation: this._animation(), onClick: onClick,
            plugins: { legend: { display: false }, tooltip: this._amountTooltip() },
            scales: {
                x: { grid: { display: false }, ticks: { font: { size: 11 }, color: this._tickColor() } },
                y: { grid: { color: this._gridColor() }, ticks: { font: { size: 11 }, color: this._tickColor() }, beginAtZero: true },
            },
        };
    }
    _lineOptions(onClick) {
        return {
            responsive: true, maintainAspectRatio: false, animation: this._animation(), onClick: onClick,
            plugins: { legend: { display: false }, tooltip: this._amountTooltip() },
            scales: {
                x: { grid: { display: false }, ticks: { font: { size: 11 }, color: this._tickColor() } },
                y: { grid: { color: this._gridColor() }, ticks: { font: { size: 11 }, color: this._tickColor() }, beginAtZero: true },
            },
        };
    }
    _doughnutOptions(percent, onClick) {
        const self = this;
        return {
            responsive: true, maintainAspectRatio: false, animation: this._animation(), cutout: "62%", onClick: onClick,
            plugins: {
                legend: { position: "bottom", labels: { usePointStyle: true, boxWidth: 8, padding: 14, font: { size: 11 }, color: this._legendColor() } },
                tooltip: {
                    padding: 10,
                    callbacks: {
                        label(ctx) {
                            if (percent) { return "  " + ctx.label + ": " + self.formatPercent(ctx.parsed); }
                            const total = ctx.dataset.data.reduce((a, b) => a + Number(b || 0), 0);
                            const share = total ? (ctx.parsed / total) * 100 : 0;
                            return "  " + ctx.label + ": " + self.formatAmount(ctx.parsed) + " (" + share.toFixed(1) + "%)";
                        },
                    },
                },
            },
        };
    }
    _clickIndex(handler) {
        return (evt, elements) => { if (elements && elements.length) { handler(elements[0].index); } };
    }
    _chartKind(key, fallback) {
        return widgetStyleStore.getChartType(key) || fallback;
    }
    _makeChart(ctx, kind, labels, values, opts) {
        const Chart = window.Chart;
        opts = opts || {};
        const accent = opts.accent || "#2563eb";
        const onClick = opts.onClick;
        const circular = kind === "doughnut" || kind === "pie";
        const horizontal = kind === "horizontalBar";
        const isLine = kind === "line" || kind === "area";

        let type = "bar";
        if (circular) { type = kind; }
        else if (isLine) { type = "line"; }

        const dataset = { label: "Revenue", data: values };
        if (circular) {
            dataset.backgroundColor = opts.accentSet
                ? this._shades(accent, values.length)
                : (opts.palette || values.map((_, i) => this._color(i)));
            dataset.borderWidth = 2;
            dataset.borderColor = this._sliceBorderColor();
            dataset.hoverOffset = 6;
        } else if (isLine) {
            dataset.borderColor = accent;
            dataset.backgroundColor = kind === "area" ? this._gradient(ctx, accent) : "transparent";
            dataset.fill = kind === "area";
            dataset.tension = 0.4;
            dataset.pointRadius = 3;
            dataset.pointBackgroundColor = accent;
            dataset.borderWidth = 2.5;
        } else {
            dataset.backgroundColor = accent;
            dataset.borderRadius = 6;
            dataset.borderSkipped = false;
            dataset.maxBarThickness = 46;
        }

        let options;
        if (circular) {
            options = this._doughnutOptions(Boolean(opts.percent), onClick);
        } else if (isLine) {
            options = this._lineOptions(onClick);
        } else {
            options = this._barOptions(onClick);
            if (horizontal) { options.indexAxis = "y"; }
        }
        return new Chart(ctx, { type, data: { labels, datasets: [dataset] }, options });
    }
    _destroyCharts() {
        this._charts.forEach((c) => { try { c.destroy(); } catch (e) { /* ignore */ } });
        this._charts = [];
    }
    _renderCharts() {
        const Chart = window.Chart;
        const data = this.state.data;
        if (!Chart || !this.rootRef.el || !data || this.state.loading) { return; }
        this._destroyCharts();
        const root = this.rootRef.el;
        const canvas = (id) => root.querySelector(`#${id}`);

        const monthly = data.monthly_revenue || [];
        if (monthly.length) {
            const ctx = canvas("inom_chart_monthly");
            if (ctx) {
                const acc = this._accent("monthly", "#16a34a");
                const kind = this._chartKind("monthly", "area");
                this._charts.push(this._makeChart(ctx, kind, monthly.map((m) => m.period), monthly.map((m) => m.revenue), {
                    accent: acc, accentSet: Boolean(widgetStyleStore.getColor("monthly")), onClick: this._clickIndex((i) => this.openMonth(i)),
                }));
            }
        }
        const mix = data.customer_mix || {};
        if ((mix.total_customers || 0) > 0) {
            const ctx = canvas("inom_chart_mix");
            if (ctx) {
                this._charts.push(new Chart(ctx, {
                    type: "doughnut",
                    data: { labels: ["New", "Repeat"], datasets: [{ data: [mix.pct_new, mix.pct_repeat], backgroundColor: ["#7c3aed", "#c4b5fd"], borderWidth: 2, borderColor: this._sliceBorderColor(), hoverOffset: 6 }] },
                    options: this._doughnutOptions(true, () => this.openNewRepeat()),
                }));
            }
        }
        const categories = data.revenue_by_category || [];
        if (categories.length) {
            const ctx = canvas("inom_chart_category");
            if (ctx) {
                const catAccent = widgetStyleStore.getColor("category");
                const kind = this._chartKind("category", "doughnut");
                this._charts.push(this._makeChart(ctx, kind, categories.map((c) => c.category_name), categories.map((c) => c.revenue), {
                    accent: catAccent || "#2563eb", accentSet: Boolean(catAccent), onClick: this._clickIndex((i) => this.openCategory(i)),
                }));
            }
        }
        const sps = data.sales_by_salesperson || [];
        if (sps.length) {
            const ctx = canvas("inom_chart_salesperson");
            if (ctx) {
                const acc = this._accent("salesperson", "#2563eb");
                const kind = this._chartKind("salesperson", "bar");
                this._charts.push(this._makeChart(ctx, kind, sps.map((s) => s.salesperson), sps.map((s) => s.revenue), {
                    accent: acc, accentSet: Boolean(widgetStyleStore.getColor("salesperson")), onClick: this._clickIndex((i) => this.openSalesperson(i)),
                }));
            }
        }
        const countries = data.sales_by_country || [];
        if (countries.length) {
            const ctx = canvas("inom_chart_country");
            if (ctx) {
                const acc = this._accent("country", "#7c3aed");
                const kind = this._chartKind("country", "bar");
                this._charts.push(this._makeChart(ctx, kind, countries.map((c) => c.country), countries.map((c) => c.revenue), {
                    accent: acc, accentSet: Boolean(widgetStyleStore.getColor("country")), onClick: this._clickIndex((i) => this.openCountry(i)),
                }));
            }
        }
        const sparkCtx = canvas("inom_spark_revenue");
        if (sparkCtx && (data.monthly_revenue || []).length > 1) {
            const vals = data.monthly_revenue.map((m) => m.revenue);
            this._charts.push(new Chart(sparkCtx, {
                type: "line",
                data: { labels: vals.map((_, i) => i), datasets: [{ data: vals, borderColor: "#16a34a", backgroundColor: this._gradient(sparkCtx, "#16a34a"), fill: true, tension: 0.45, pointRadius: 0, borderWidth: 2 }] },
                options: {
                    responsive: true, maintainAspectRatio: false, animation: this._animation(),
                    plugins: { legend: { display: false }, tooltip: { enabled: false } },
                    scales: { x: { display: false }, y: { display: false } },
                },
            }));
        }
        const cmp = this.comparison;
        if (cmp) {
            const revCtx = canvas("inom_chart_cmp_rev");
            if (revCtx) {
                this._charts.push(new Chart(revCtx, {
                    type: "bar",
                    data: { labels: ["Current", "Previous"], datasets: [{ label: "Revenue", data: [cmp.curRevenue, cmp.prevRevenue], backgroundColor: ["#2563eb", "#cbd5ea"], borderRadius: 6, borderSkipped: false, maxBarThickness: 64 }] },
                    options: this._barOptions(null),
                }));
            }
            const ordCtx = canvas("inom_chart_cmp_ord");
            if (ordCtx) {
                this._charts.push(new Chart(ordCtx, {
                    type: "bar",
                    data: { labels: ["Current", "Previous"], datasets: [{ label: "Orders", data: [cmp.curOrders, cmp.prevOrders], backgroundColor: ["#16a34a", "#cdead9"], borderRadius: 6, borderSkipped: false, maxBarThickness: 64 }] },
                    options: this._plainBarOptions(),
                }));
            }
        }
    }
}

InomSalesDashboard.template = "inom_advance_sales_dashboard.Dashboard";
InomSalesDashboard.props = { "*": true };

registry.category("actions").add("inom_advance_sales_dashboard.dashboard", InomSalesDashboard);
