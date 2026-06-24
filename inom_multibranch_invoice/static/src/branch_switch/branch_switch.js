/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { user } from "@web/core/user";

export class InomBranchSwitcher extends Component {
    static template = "inom_multibranch_invoice.BranchSwitcher";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.state = useState({
            open: false,
            current: null,
            branches: [],
        });

        onWillStart(async () => {
            await this.loadBranches();
        });
    }

    async loadBranches() {
        try {
            const [rec] = await this.orm.read(
                "res.users",
                [user.userId],
                ["inom_default_branch_id", "inom_allowed_branch_ids"]
            );
            const allowedIds = rec.inom_allowed_branch_ids || [];
            if (allowedIds.length) {
                this.state.branches = await this.orm.searchRead(
                    "inom.branch",
                    [["id", "in", allowedIds]],
                    ["id", "name", "code"]
                );
            }
            this.state.current = rec.inom_default_branch_id || null;
        } catch {
            this.state.branches = [];
        }
    }

    get currentLabel() {
        if (this.state.current) {
            return this.state.current[1];
        }
        return "No Branch";
    }

    get hasMultiple() {
        return this.state.branches.length > 1;
    }

    toggle() {
        this.state.open = !this.state.open;
    }

    async selectBranch(branchId) {
        this.state.open = false;
        try {
            await this.orm.write("res.users", [user.userId], {
                inom_default_branch_id: branchId,
            });
            window.location.reload();
        } catch {
            // ignore - keep current selection
        }
    }
}

export const systrayItem = {
    Component: InomBranchSwitcher,
};

registry
    .category("systray")
    .add("inom_multibranch_invoice.BranchSwitcher", systrayItem, { sequence: 30 });
