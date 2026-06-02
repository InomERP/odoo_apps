/** @odoo-module **/

import { Component, onWillStart, onMounted, onWillUnmount, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class AuditDashboard extends Component {
    static template = "inom_audit_trail.AuditDashboard";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({
            loading: true,
            now: this._clock(),
            showUsers: false,
            data: this._empty(),
        });

        onWillStart(async () => {
            await this.load();
        });
        onMounted(() => {
            this.dataTimer = setInterval(() => this.load(), 8000);
            this.clockTimer = setInterval(() => {
                this.state.now = this._clock();
            }, 1000);
        });
        onWillUnmount(() => {
            clearInterval(this.dataTimer);
            clearInterval(this.clockTimer);
        });
    }

    _empty() {
        return {
            active_now: 0, online_users: [], today: 0, yesterday: 0,
            buckets: new Array(12).fill(0), current_bucket: 0,
            active_rules: 0, total_rules: 0, objects_tracked: 0, rules: [],
        };
    }

    _clock() {
        return new Date().toLocaleTimeString();
    }

    async load() {
        try {
            const data = await this.orm.call("inom.audit.trail.rule", "get_dashboard_data", []);
            this.state.data = data;
        } catch (e) {
            // keep last known data on error
        } finally {
            this.state.loading = false;
        }
    }

    get onlineUsers() {
        return this.state.data.online_users || [];
    }

    get onlineAvatars() {
        return this.onlineUsers.slice(0, 4);
    }

    get delta() {
        const { today, yesterday } = this.state.data;
        if (!yesterday) {
            return { txt: today ? "+100%" : "0%", cls: today ? "up" : "flat" };
        }
        const p = Math.round(((today - yesterday) / yesterday) * 100);
        return { txt: (p > 0 ? "+" : "") + p + "%", cls: p > 0 ? "up" : p < 0 ? "down" : "flat" };
    }

    get maxBucket() {
        return Math.max(1, ...this.state.data.buckets);
    }

    barHeight(v) {
        return Math.max(8, Math.round((v / this.maxBucket) * 100));
    }

    initials(name) {
        return (name || "?").split(" ").map((w) => w[0]).slice(0, 2).join("").toUpperCase();
    }

    toggleUsers() {
        this.state.showUsers = !this.state.showUsers;
    }

    openLogs() {
        this.action.doAction("inom_audit_trail.action_audit_log");
    }

    openRules() {
        this.action.doAction("inom_audit_trail.action_audit_rule");
    }

    openRule(id) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "inom.audit.trail.rule",
            res_id: id,
            views: [[false, "form"]],
            target: "current",
        });
    }

    newRule() {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "inom.audit.trail.rule",
            views: [[false, "form"]],
            target: "current",
        });
    }
}

registry.category("actions").add("inom_audit_trail.dashboard", AuditDashboard);
