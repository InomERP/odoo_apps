/** @odoo-module **/
import { registry } from "@web/core/registry";
import { Component, onWillStart, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class AdmissionsDashboard extends Component {
    static template = "inom_university_admission.AdmissionsDashboard";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({
            loading: true,
            dateRange: "all",
            programId: false,
            data: {
                kpis: {},
                programs: [],
                statuses: [],
                trend: [],
                recent: [],
                all_programs: [],
            },
        });
        onWillStart(() => this.load());
    }

    async load() {
        this.state.loading = true;
        try {
            const data = await this.orm.call(
                "univ.admission.dashboard",
                "get_admissions_dashboard_data",
                [],
                {
                    date_range: this.state.dateRange,
                    program_id: this.state.programId || false,
                }
            );
            this.state.data = data;
        } catch (error) {
            this.state.data = {
                kpis: {}, programs: [], statuses: [],
                trend: [], recent: [], all_programs: [],
            };
        } finally {
            this.state.loading = false;
        }
    }

    async setDateRange(range) {
        this.state.dateRange = range;
        await this.load();
    }

    async onProgramChange(ev) {
        this.state.programId = parseInt(ev.target.value, 10) || false;
        await this.load();
    }

    // ----- KPI cards configuration -----
    get kpiCards() {
        const k = this.state.data.kpis || {};
        return [
            { key: "total", label: "Total Applications", value: k.total || 0, cls: "o_ad_card--primary", icon: "fa-folder-open" },
            { key: "today", label: "Submitted Today", value: k.today || 0, cls: "o_ad_card--blue", icon: "fa-calendar-check-o" },
            { key: "month", label: "This Month", value: k.month || 0, cls: "o_ad_card--indigo", icon: "fa-calendar" },
            { key: "verification", label: "Under Verification", value: k.verification || 0, cls: "o_ad_card--amber", icon: "fa-search" },
            { key: "offers", label: "Offers Issued", value: k.offers || 0, cls: "o_ad_card--teal", icon: "fa-envelope-open-o" },
            { key: "confirmed", label: "Admissions Confirmed", value: k.confirmed || 0, cls: "o_ad_card--green", icon: "fa-check-circle" },
            { key: "rejected", label: "Rejected", value: k.rejected || 0, cls: "o_ad_card--red", icon: "fa-times-circle" },
        ];
    }

    domainForKpi(key) {
        const base = this.state.programId ? [["program_id", "=", this.state.programId]] : [];
        const map = {
            total: [],
            verification: [["stage_id.code", "=", "document_verification"]],
            offers: [["offer_state", "in", ["sent", "accepted"]]],
            confirmed: [["is_enrolled", "=", true]],
            rejected: [["stage_id.is_rejected", "=", true]],
        };
        return base.concat(map[key] || []);
    }

    openApplications(domain, name) {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: name || "Applications",
            res_model: "univ.applicant",
            views: [[false, "list"], [false, "form"]],
            domain: domain || [],
            target: "current",
        });
    }

    onKpiClick(card) {
        if (["today", "month"].includes(card.key)) {
            return; // date KPIs are informational
        }
        this.openApplications(this.domainForKpi(card.key), card.label);
    }

    openApplicant(rec) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "univ.applicant",
            res_id: rec.id,
            views: [[false, "form"]],
            target: "current",
        });
    }

    // ----- Chart helpers (pure CSS/SVG, no external library) -----
    get programChart() {
        const rows = this.state.data.programs || [];
        const max = Math.max(1, ...rows.map((r) => r.value));
        return rows.map((r) => ({ ...r, pct: Math.round((r.value / max) * 100) }));
    }

    get statusPalette() {
        return ["#7c3aed", "#2563eb", "#0d9488", "#f59e0b", "#16a34a", "#dc2626", "#6366f1", "#64748b"];
    }

    get statusChart() {
        const rows = this.state.data.statuses || [];
        const total = rows.reduce((s, r) => s + r.value, 0) || 1;
        const palette = this.statusPalette;
        let acc = 0;
        const segments = rows.map((r, i) => {
            const start = (acc / total) * 360;
            acc += r.value;
            const end = (acc / total) * 360;
            return {
                label: r.label,
                value: r.value,
                color: palette[i % palette.length],
                start,
                end,
                pct: Math.round((r.value / total) * 100),
            };
        });
        const gradient = segments
            .map((s) => `${s.color} ${s.start}deg ${s.end}deg`)
            .join(", ");
        return { segments, gradient: `conic-gradient(${gradient})`, total };
    }

    get trendChart() {
        const rows = this.state.data.trend || [];
        const max = Math.max(1, ...rows.map((r) => r.value));
        return rows.map((r) => ({ ...r, pct: Math.round((r.value / max) * 100) }));
    }
}

registry.category("actions").add("inom_admissions_dashboard", AdmissionsDashboard);
