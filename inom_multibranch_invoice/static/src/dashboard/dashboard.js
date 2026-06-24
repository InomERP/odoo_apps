/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class InomBranchDashboard extends Component {
    static template = "inom_multibranch_invoice.Dashboard";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({
            loading: true,
            data: {
                currency_symbol: "",
                currency_position: "before",
                total_sales: 0,
                total_purchase: 0,
                total_branches: 0,
                branches: [],
            },
        });

        onWillStart(async () => {
            await this.loadData();
        });
    }

    async loadData() {
        this.state.loading = true;
        try {
            const data = await this.orm.call(
                "inom.branch.dashboard",
                "get_dashboard_data",
                []
            );
            this.state.data = data;
        } catch {
            this.state.data.branches = [];
        }
        this.state.loading = false;
    }

    get netTotal() {
        return (this.state.data.total_sales || 0) - (this.state.data.total_purchase || 0);
    }

    get totalInvoices() {
        return this.state.data.branches.reduce((s, b) => s + (b.invoice_count || 0), 0);
    }

    get maxValue() {
        let max = 0;
        for (const b of this.state.data.branches) {
            max = Math.max(max, b.sales || 0, b.purchase || 0);
        }
        return max || 1;
    }

    barWidth(value) {
        const pct = (Math.abs(value || 0) / this.maxValue) * 100;
        return Math.max(pct, 2).toFixed(1) + "%";
    }

    formatAmount(value) {
        const d = this.state.data;
        const amount = Number(value || 0).toLocaleString(undefined, {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        });
        if (d.currency_position === "after") {
            return `${amount} ${d.currency_symbol}`;
        }
        return `${d.currency_symbol} ${amount}`;
    }

    openBranchInvoices(branchId) {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Customer Invoices",
            res_model: "account.move",
            domain: [
                ["move_type", "=", "out_invoice"],
                ["inom_branch_id", "=", branchId],
            ],
            views: [
                [false, "list"],
                [false, "form"],
            ],
            target: "current",
        });
    }
}

registry.category("actions").add("inom_branch_dashboard", InomBranchDashboard);