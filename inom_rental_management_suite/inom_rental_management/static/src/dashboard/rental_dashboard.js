import { Component, onWillStart, useState } from "@odoo/owl";
import { deserializeDateTime } from "@web/core/l10n/dates";
import { registry } from "@web/core/registry";
import { user } from "@web/core/user";
import { useService } from "@web/core/utils/hooks";

// Headline cards: colour, icon and background picture of each figure.
const KPI_STYLE = {
    total: { color: "blue", icon: "fa-home", mark: "fa-building" },
    available: { color: "green", icon: "fa-calendar-check-o", mark: "fa-home" },
    for_sale: { color: "purple", icon: "fa-tag", mark: "fa-tag" },
    for_rent: { color: "orange", icon: "fa-key", mark: "fa-key" },
    occupied: { color: "teal", icon: "fa-user", mark: "fa-users" },
    vacant: { color: "red", icon: "fa-file-text", mark: "fa-home" },
};

const QUICK_STYLE = {
    property: { color: "blue", icon: "fa-home" },
    lease: { color: "green", icon: "fa-file-text" },
    payment: { color: "purple", icon: "fa-database" },
    report: { color: "orange", icon: "fa-bar-chart" },
};

const QUOTES = [
    "Real estate is not just about property, it's about people.",
    "Don't wait to buy real estate. Buy real estate and wait.",
    "Every great tenancy starts with a well-kept home.",
    "Landlords grow rich in their sleep; good records help them sleep.",
    "Location matters, but service keeps tenants.",
    "A home is the starting place of love, hope and dreams.",
];

const MINI_STYLE = {
    active_contracts: { color: "green", icon: "fa-file-text", empty: "No active contracts" },
    expiring: { color: "blue", icon: "fa-clock-o", empty: "No leases expiring" },
    upcoming_due: { color: "red", icon: "fa-usd", empty: "No upcoming rent due" },
    sold: { color: "green", icon: "fa-shopping-cart" },
    booked: { color: "purple", icon: "fa-calendar" },
    rent_invoiced: { color: "green", icon: "fa-file-text-o" },
    rent_collected: { color: "blue", icon: "fa-money" },
    overdue: { color: "purple", icon: "fa-exclamation-circle" },
};

const STATUS_STYLE = {
    available: { color: "green", icon: "fa-check-circle" },
    rented: { color: "blue", icon: "fa-key" },
    booked: { color: "orange", icon: "fa-bookmark" },
    sold: { color: "purple", icon: "fa-handshake-o" },
    draft: { color: "pink", icon: "fa-pencil" },
};

const ACTIVITY_STYLE = {
    property: { color: "green", icon: "fa-home" },
    lease: { color: "blue", icon: "fa-file-text" },
    payment: { color: "purple", icon: "fa-usd" },
    sale: { color: "orange", icon: "fa-handshake-o" },
};

// Line chart drawing area, in SVG units
const CHART = { width: 560, height: 220, left: 52, right: 12, top: 12, bottom: 28 };

export class RentalDashboard extends Component {
    static template = "inom_rental_management.RentalDashboard";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.chart = CHART;
        this.state = useState({ period: "this_month", chartRange: "last_6_months", data: null, loading: true });
        this.userName = (user.name || "").split(" ")[0];
        this.bannerUrl = "/inom_rental_management/static/src/img/dashboard_banner.svg";
        this.houseUrl = "/inom_rental_management/static/src/img/dashboard_house.svg";
        onWillStart(() => this.load());
    }

    async load() {
        this.state.loading = true;
        this.state.data = await this.orm.call("property.dashboard", "get_dashboard_data", [
            this.state.period,
            this.state.chartRange,
        ]);
        this.state.loading = false;
    }

    async onPeriodChange(ev) {
        this.state.period = ev.target.value;
        await this.load();
    }

    async onChartRangeChange(ev) {
        this.state.chartRange = ev.target.value;
        await this.load();
    }

    get greeting() {
        const hour = new Date().getHours();
        return hour < 12 ? "Good Morning" : hour < 17 ? "Good Afternoon" : "Good Evening";
    }

    get quote() {
        const start = new Date(new Date().getFullYear(), 0, 0);
        const day = Math.floor((new Date() - start) / 86400000);
        return QUOTES[day % QUOTES.length];
    }

    get periodLabel() {
        const found = (this.state.data?.periods || []).find((p) => p[0] === this.state.period);
        return found ? found[1] : "This Period";
    }

    get quickActions() {
        return (this.state.data?.quick_actions || []).map((qa) => ({ ...qa, ...QUICK_STYLE[qa.key] }));
    }

    miniHint(key) {
        const tl = this.tile(key);
        return !tl.raw && MINI_STYLE[key]?.empty ? MINI_STYLE[key].empty : false;
    }

    // Change of the property count since the start of the period
    get totalTrend() {
        const summary = this.state.data.summary;
        const added = summary.total - summary.total_before_period;
        const percent = summary.total_before_period ? Math.round((100 * added) / summary.total_before_period) : 0;
        if (!added) {
            return { arrow: "fa-minus", tone: "muted", text: "No change this period" };
        }
        return {
            arrow: added > 0 ? "fa-arrow-up" : "fa-arrow-down",
            tone: added > 0 ? "up" : "down",
            text: summary.total_before_period ? `${Math.abs(percent)}% vs start of period` : `${added} added this period`,
        };
    }

    open(action) {
        if (action) {
            this.action.doAction(action);
        }
    }

    tile(key) {
        for (const section of Object.values(this.state.data?.tiles || {})) {
            const found = section.find((tile) => tile.key === key);
            if (found) {
                return found;
            }
        }
        return { value: 0, raw: 0, hint: false, action: false, label: "" };
    }

    kpiStyle(key) {
        return KPI_STYLE[key];
    }

    miniStyle(key) {
        return MINI_STYLE[key] || { color: "gray", icon: "fa-circle" };
    }

    plural(count, singular, pluralWord) {
        return `${count} ${count === 1 ? singular : pluralWord}`;
    }

    percent(value, base) {
        return base ? Math.round((100 * value) / base) : 0;
    }

    // Small caption under each headline figure
    kpiHint(key) {
        const total = this.tile("total").value;
        const rental = this.tile("for_rent").value;
        switch (key) {
            case "occupied":
            case "vacant":
                return `${this.percent(this.tile(key).value, rental)}% of rental properties`;
            default:
                return `${this.percent(this.tile(key).value, total)}% of total`;
        }
    }

    get isEmpty() {
        return this.state.data && !this.state.data.summary.total;
    }

    // Donut of properties by status
    get statusSegments() {
        const items = (this.state.data?.charts.status || []).filter((item) => item.value > 0);
        const total = items.reduce((sum, item) => sum + item.value, 0);
        const radius = 54;
        const circumference = 2 * Math.PI * radius;
        let offset = 0;
        return items.map((item) => {
            const length = total ? (item.value / total) * circumference : 0;
            const segment = {
                ...item,
                color: STATUS_STYLE[item.key]?.color || "gray",
                dasharray: `${length} ${circumference - length}`,
                dashoffset: -offset,
            };
            offset += length;
            return segment;
        });
    }

    get statusLegend() {
        const total = this.state.data?.summary.total || 0;
        return (this.state.data?.charts.status || []).map((item) => ({
            ...item,
            ...(STATUS_STYLE[item.key] || { color: "gray", icon: "fa-circle" }),
            percent: this.percent(item.value, total),
        }));
    }

    // Line chart of rent invoiced against collected
    get incomeChart() {
        const months = this.state.data?.charts.income || [];
        const { width, height, left, right, top, bottom } = CHART;
        const plotWidth = width - left - right;
        const plotHeight = height - top - bottom;
        const max = niceMax(Math.max(0, ...months.map((m) => Math.max(m.invoiced, m.collected))));
        const x = (index) => left + (months.length > 1 ? (index * plotWidth) / (months.length - 1) : plotWidth / 2);
        const y = (value) => top + plotHeight - (value / max) * plotHeight;
        const series = (key) => {
            const points = months.map((m, index) => ({
                x: x(index),
                y: y(m[key]),
                title: `${m.label}: ${m[`${key}_display`]}`,
            }));
            const line = points.map((p, index) => `${index ? "L" : "M"}${p.x},${p.y}`).join(" ");
            const baseline = top + plotHeight;
            const area = points.length
                ? `${line} L${points.at(-1).x},${baseline} L${points[0].x},${baseline} Z`
                : "";
            return { points, line, area };
        };
        const ticks = [0, 0.25, 0.5, 0.75, 1].map((step) => ({
            y: y(step * max),
            label: compactNumber(step * max),
        }));
        return {
            ticks,
            labels: months
                .map((m, index) => ({ x: x(index), text: m.short_label, key: m.label, index }))
                .filter((l) => months.length <= 12 || l.index % 5 === 0 || l.index === months.length - 1),
            invoiced: series("invoiced"),
            collected: series("collected"),
        };
    }

    get activity() {
        return (this.state.data?.lists.activity || []).slice(0, 5).map((event) => ({
            ...event,
            ...(ACTIVITY_STYLE[event.kind] || { color: "gray", icon: "fa-circle" }),
            ago: deserializeDateTime(event.when).toRelative(),
        }));
    }

    newProperty() {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "property.property",
            views: [[false, "form"]],
            target: "current",
        });
    }
}

// Round the chart maximum up to 1, 2, 2.5 or 5 times a power of ten
function niceMax(value) {
    if (value <= 0) {
        return 1;
    }
    const power = 10 ** Math.floor(Math.log10(value));
    const step = [1, 2, 2.5, 5, 10].find((s) => s * power >= value);
    return step * power;
}

function compactNumber(value) {
    if (value >= 1e6) {
        return `${+(value / 1e6).toFixed(1)}M`;
    }
    if (value >= 1e3) {
        return `${+(value / 1e3).toFixed(1)}k`;
    }
    return `${+value.toFixed(value < 10 ? 2 : 0)}`;
}

registry.category("actions").add("inom_rental_management.dashboard", RentalDashboard);
