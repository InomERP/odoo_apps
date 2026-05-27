/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, useState } from "@odoo/owl";

export class HospitalDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({
            loading: true,
            data: null,
        });

        onWillStart(async () => {
            await this._load();
        });
    }

    async _load() {
        this.state.loading = true;
        this.state.data = await this.orm.call("oeh.dashboard", "get_dashboard_data", []);
        this.state.loading = false;
    }

    async onRefresh() {
        await this._load();
    }

    /** Format a number as currency using the company currency. */
    formatMoney(value) {
        const d = this.state.data;
        const num = Number(value || 0).toLocaleString(undefined, {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        });
        if (!d || !d.currency_symbol) {
            return num;
        }
        return d.currency_position === "after"
            ? `${num} ${d.currency_symbol}`
            : `${d.currency_symbol} ${num}`;
    }

    /** Largest count in a breakdown list (used to scale bar widths). */
    maxOf(list) {
        return Math.max(1, ...(list || []).map((i) => i.count));
    }

    barWidth(item, list) {
        return `${Math.round((item.count / this.maxOf(list)) * 100)}%`;
    }

    /** Open a standard list/form action for the given model. */
    openModel(model, name) {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: name,
            res_model: model,
            views: [
                [false, "list"],
                [false, "form"],
            ],
            target: "current",
        });
    }
}

HospitalDashboard.template = "inom_healthcare_system.Dashboard";

registry.category("actions").add("inom_healthcare_system.dashboard", HospitalDashboard);
