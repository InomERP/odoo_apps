/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, useState, onWillStart } from "@odoo/owl";
import { makePosStore } from "./pos_store";

/* ============================================================
 *  PATIENT MODAL
 * ============================================================ */
export class PatientModal extends Component {
    static template = "inom_healthcare_pos.PatientModal";
    static props = { store: Object };
    setup() {
        this.store = useState(this.props.store);
    }
}

/* ============================================================
 *  OPENING (cash control) SCREEN
 * ============================================================ */
export class OpeningScreen extends Component {
    static template = "inom_healthcare_pos.OpeningScreen";
    static props = { store: Object };
    setup() {
        this.store = useState(this.props.store);
    }
}

/* ============================================================
 *  CONFIG / TERMINAL PICKER
 * ============================================================ */
export class ConfigScreen extends Component {
    static template = "inom_healthcare_pos.ConfigScreen";
    static props = { store: Object };
    setup() {
        this.store = useState(this.props.store);
    }
}

/* ============================================================
 *  PRODUCT (main) SCREEN
 * ============================================================ */
export class ProductScreen extends Component {
    static template = "inom_healthcare_pos.ProductScreen";
    static props = { store: Object };
    setup() {
        this.store = useState(this.props.store);
        this.numpadKeys = ["1", "2", "3", "4", "5", "6", "7", "8", "9", ".", "0", "backspace"];
    }
    iconFor(type) {
        const map = {
            consultation: "user-md", lab: "flask", radiology: "camera",
            pharmacy: "medkit", treatment: "heartbeat", procedure: "scissors",
        };
        return map[type] || "stethoscope";
    }
}

/* ============================================================
 *  PAYMENT SCREEN
 * ============================================================ */
export class PaymentScreen extends Component {
    static template = "inom_healthcare_pos.PaymentScreen";
    static props = { store: Object };
    setup() {
        this.store = useState(this.props.store);
    }
}

/* ============================================================
 *  RECEIPT SCREEN
 * ============================================================ */
export class ReceiptScreen extends Component {
    static template = "inom_healthcare_pos.ReceiptScreen";
    static props = { store: Object };
    setup() {
        this.store = useState(this.props.store);
    }
    print() {
        window.print();
    }
}

/* ============================================================
 *  CLOSING SUMMARY SCREEN
 * ============================================================ */
export class ClosingScreen extends Component {
    static template = "inom_healthcare_pos.ClosingScreen";
    static props = { store: Object };
    setup() {
        this.store = useState(this.props.store);
    }
}

/* ============================================================
 *  ROOT APP
 * ============================================================ */
export class HealthcarePosApp extends Component {
    static template = "inom_healthcare_pos.App";
    static components = {
        ConfigScreen, OpeningScreen, ProductScreen,
        PaymentScreen, ReceiptScreen, ClosingScreen, PatientModal,
    };
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.action = useService("action");

        this.store = makePosStore(this.orm, this.notification, this.action);
        this.state = useState(this.store);

        const action = this.props.action || {};
        const params = action.params || (action.context || {});
        this.configId = params.config_id || false;

        onWillStart(async () => {
            if (this.configId) {
                await this.store.loadConfig(this.configId);
            } else {
                await this.store.loadConfigList();
            }
        });
    }

    exit() {
        this.action.doAction("inom_healthcare_pos.action_healthcare_pos_dashboard");
    }
}

registry.category("actions").add("inom_healthcare_pos.app", HealthcarePosApp);
