/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, useState, onWillStart } from "@odoo/owl";

/* ============================================================
 *  HEALTHCARE POS DASHBOARD
 *  ----------------------------------------------------------
 *  The backend landing page for the "Point of Sale" menu.
 *  Mirrors the standard Odoo POS dashboard: a responsive grid
 *  of terminal cards, each with its own company / branch /
 *  currency and live-session status, plus a primary
 *  "New Session" / "Continue Selling" action and a kebab menu
 *  for Orders / Sessions / Settings. Several terminals can be
 *  opened at once, which is how multi-location selling works.
 * ============================================================ */
export class HealthcarePosDashboard extends Component {
    static template = "inom_healthcare_pos.Dashboard";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
        this.state = useState({ cards: [], loading: true, menuOpenId: null });
        onWillStart(async () => {
            await this.load();
        });
    }

    async load() {
        this.state.loading = true;
        try {
            this.state.cards = await this.orm.call(
                "healthcare.pos.config", "get_pos_dashboard_data", []
            );
        } catch (e) {
            this.notification.add("Could not load the Point of Sale dashboard.", {
                type: "danger",
            });
            this.state.cards = [];
        }
        this.state.loading = false;
    }

    toggleMenu(id) {
        this.state.menuOpenId = this.state.menuOpenId === id ? null : id;
    }

    /** Launch the custom POS UI for a terminal. The POS store decides
     *  whether to show the opening-cash screen (no open session yet) or
     *  jump straight into selling (an open session is resumed). */
    openPos(card) {
        this.state.menuOpenId = null;
        this.action.doAction({
            type: "ir.actions.client",
            tag: "inom_healthcare_pos.app",
            params: { config_id: card.id },
        });
    }

    async viewOrders(card) {
        this.state.menuOpenId = null;
        const action = await this.orm.call(
            "healthcare.pos.config", "action_view_orders", [[card.id]]
        );
        this.action.doAction(action);
    }

    async viewSessions(card) {
        this.state.menuOpenId = null;
        const action = await this.orm.call(
            "healthcare.pos.config", "action_view_sessions", [[card.id]]
        );
        this.action.doAction(action);
    }

    editConfig(card) {
        this.state.menuOpenId = null;
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Point of Sale Settings",
            res_model: "healthcare.pos.config",
            res_id: card.id,
            views: [[false, "form"]],
            target: "current",
        });
    }

    newConfig() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "New Point of Sale",
            res_model: "healthcare.pos.config",
            views: [[false, "form"]],
            target: "current",
        });
    }
}

registry.category("actions").add("inom_healthcare_pos.dashboard", HealthcarePosDashboard);
