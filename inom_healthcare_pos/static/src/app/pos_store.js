/** @odoo-module **/

import { reactive } from "@odoo/owl";

/**
 * Central reactive state + business logic for the Healthcare POS.
 * One instance is created by the root component and shared with every screen.
 * Components subscribe to changes with `useState(store)`.
 */
export class PosStore {
    constructor(orm, notification, action) {
        this.orm = orm;
        this.notification = notification;
        this.action = action;

        // --- bootstrap data (filled by load) ---
        this.config = null;
        this.company = null;
        this.currency = { symbol: "$", position: "before", decimals: 2 };
        this.categories = [];
        this.services = [];
        this.paymentMethods = [];
        this.patients = [];
        this.doctors = [];
        this.session = null;

        // --- POS type / dynamic workflow (driven by config.pos_type) ---
        this.posType = "general";
        this.posTypeLabel = "";
        this.posTypeIcon = "fa-hospital-o";
        this.posTypeColor = "#0d9488";
        this.features = { show_doctor: true };
        this.workflowActions = [];

        // --- live UI state ---
        this.screen = "loading";        // loading|config|opening|product|payment|receipt|closing
        this.loadingError = null;
        this.configList = [];           // for the terminal picker
        this.activeCategoryId = null;
        this.searchTerm = "";
        this.numpadMode = "qty";        // qty|price|disc

        // --- current order ---
        this.order = this._emptyOrder();

        // --- payment ---
        this.payments = [];             // [{methodId, name, isCash, amount}]

        // --- receipt / closing ---
        this.receipt = null;
        this.closingReport = null;

        // --- patient modal ---
        this.patientModalOpen = false;
        this.patientCreateMode = false;
        this.patientSearch = "";
        this.newPatient = this._emptyPatient();

        // --- opening / closing inputs ---
        this.openingBalance = 0;
        this.closingBalance = 0;
    }

    _emptyOrder() {
        return {
            lines: [],          // [{id, serviceId, name, type, qty, priceUnit, discount, taxPercent}]
            patient: null,
            doctor: null,
            note: "",
            selectedLineId: null,
            seq: 1,
        };
    }

    _emptyPatient() {
        return { name: "", phone: "", email: "", gender: "", age: "", blood_group: "", address: "" };
    }

    // ------------------------------------------------------------------
    // Bootstrap
    // ------------------------------------------------------------------
    async loadConfigList() {
        this.configList = await this.orm.searchRead(
            "healthcare.pos.config",
            [["active", "=", true]],
            ["name", "campus_id", "company_id", "currency_id", "current_session_state"]
        );
        this.screen = "config";
    }

    async loadConfig(configId) {
        this.screen = "loading";
        try {
            const data = await this.orm.call(
                "healthcare.pos.config", "load_pos_data", [configId]);
            this.config = data.config;
            this.company = data.company;
            this.currency = data.currency;
            this.posType = data.config.pos_type || "general";
            this.posTypeLabel = data.config.pos_type_label || "";
            this.posTypeIcon = data.config.pos_type_icon || "fa-hospital-o";
            this.posTypeColor = data.config.pos_type_color || "#0d9488";
            this.features = data.config.features || { show_doctor: true };
            this.workflowActions = data.config.workflow_actions || [];
            this.categories = data.categories;
            this.services = data.services;
            this.paymentMethods = data.payment_methods;
            this.patients = data.patients;
            this.doctors = data.doctors;
            this.session = data.session || null;
            this.activeCategoryId = this.categories.length ? this.categories[0].id : null;

            if (this.session && this.session.state === "opened") {
                this.screen = "product";
            } else {
                this.screen = "opening";
            }
        } catch (e) {
            this.loadingError = (e && e.message && e.message.data && e.message.data.message)
                || (e && e.message) || "Failed to load the Point of Sale.";
            this.screen = "config";
            this.notification.add(this.loadingError, { type: "danger" });
        }
    }

    // ------------------------------------------------------------------
    // Session lifecycle
    // ------------------------------------------------------------------
    async openSession() {
        try {
            this.session = await this.orm.call(
                "healthcare.pos.session", "open_session_from_ui",
                [this.config.id, Number(this.openingBalance) || 0]);
            this.screen = "product";
        } catch (e) {
            this.notification.add("Could not open the session.", { type: "danger" });
        }
    }

    async closeSession() {
        try {
            this.closingReport = await this.orm.call(
                "healthcare.pos.session", "close_session_from_ui",
                [[this.session.id], Number(this.closingBalance) || 0]);
            this.session = null;
            this.screen = "closing";
        } catch (e) {
            const msg = (e && e.message && e.message.data && e.message.data.message) || "Could not close the session.";
            this.notification.add(msg, { type: "danger" });
        }
    }

    // ------------------------------------------------------------------
    // Catalogue helpers
    // ------------------------------------------------------------------
    get visibleServices() {
        const term = this.searchTerm.trim().toLowerCase();
        return this.services.filter((s) => {
            const catOk = !this.activeCategoryId || s.category_id === this.activeCategoryId;
            const termOk = !term
                || s.name.toLowerCase().includes(term)
                || (s.code || "").toLowerCase().includes(term);
            return catOk && termOk;
        });
    }

    categoryById(id) {
        return this.categories.find((c) => c.id === id);
    }

    // ------------------------------------------------------------------
    // Order / cart
    // ------------------------------------------------------------------
    addService(service) {
        const existing = this.order.lines.find((l) => l.serviceId === service.id);
        if (existing) {
            existing.qty += 1;
            this.order.selectedLineId = existing.id;
            return;
        }
        const line = {
            id: this.order.seq++,
            serviceId: service.id,
            name: service.name,
            type: service.service_type,
            qty: 1,
            priceUnit: service.price,
            discount: 0,
            taxPercent: service.tax_percent,
        };
        this.order.lines.push(line);
        this.order.selectedLineId = line.id;
    }

    selectLine(lineId) {
        this.order.selectedLineId = lineId;
        this.numpadMode = "qty";
    }

    removeLine(lineId) {
        this.order.lines = this.order.lines.filter((l) => l.id !== lineId);
        if (this.order.selectedLineId === lineId) {
            this.order.selectedLineId = this.order.lines.length
                ? this.order.lines[this.order.lines.length - 1].id : null;
        }
    }

    get selectedLine() {
        return this.order.lines.find((l) => l.id === this.order.selectedLineId) || null;
    }

    // numpad handling --------------------------------------------------
    setNumpadMode(mode) {
        this.numpadMode = mode;
    }

    numpadInput(key) {
        const line = this.selectedLine;
        if (!line) {
            return;
        }
        const field = this.numpadMode === "qty" ? "qty"
            : this.numpadMode === "price" ? "priceUnit" : "discount";
        let current = String(line[field] ?? 0);

        if (key === "backspace") {
            current = current.length > 1 ? current.slice(0, -1) : "0";
        } else if (key === "+/-") {
            current = current.startsWith("-") ? current.slice(1) : "-" + current;
        } else if (key === ".") {
            if (!current.includes(".")) {
                current += ".";
            }
        } else {
            current = current === "0" ? key : current + key;
        }
        const num = parseFloat(current);
        line[field] = isNaN(num) ? 0 : (current.endsWith(".") ? current : num);
    }

    lineSubtotal(line) {
        const gross = (Number(line.qty) || 0) * (Number(line.priceUnit) || 0);
        return gross * (1 - (Number(line.discount) || 0) / 100);
    }
    lineTax(line) {
        return this.lineSubtotal(line) * (Number(line.taxPercent) || 0) / 100;
    }
    lineTotal(line) {
        return this.lineSubtotal(line) + this.lineTax(line);
    }

    get amountUntaxed() {
        return this.order.lines.reduce((s, l) => s + this.lineSubtotal(l), 0);
    }
    get amountTax() {
        return this.order.lines.reduce((s, l) => s + this.lineTax(l), 0);
    }
    get amountTotal() {
        return this.order.lines.reduce((s, l) => s + this.lineTotal(l), 0);
    }

    // ------------------------------------------------------------------
    // Patient
    // ------------------------------------------------------------------
    get filteredPatients() {
        const term = this.patientSearch.trim().toLowerCase();
        if (!term) {
            return this.patients.slice(0, 60);
        }
        return this.patients.filter((p) =>
            p.name.toLowerCase().includes(term)
            || (p.ref || "").toLowerCase().includes(term)
            || (p.phone || "").includes(term)
        ).slice(0, 60);
    }

    openPatientModal() {
        this.patientModalOpen = true;
        this.patientCreateMode = false;
        this.patientSearch = "";
    }
    closePatientModal() {
        this.patientModalOpen = false;
        this.patientCreateMode = false;
        this.newPatient = this._emptyPatient();
    }
    selectPatient(patient) {
        this.order.patient = patient;
        this.closePatientModal();
    }
    clearPatient() {
        this.order.patient = null;
    }

    // ------------------------------------------------------------------
    // Type-specific workflow actions (toolbar buttons)
    // ------------------------------------------------------------------
    runWorkflowAction(action) {
        // In-POS patient actions
        if (action.mode === "patient_create") {
            this.openPatientModal();
            this.patientCreateMode = true;
            return;
        }
        if (action.mode === "patient_select") {
            this.openPatientModal();
            this.patientCreateMode = false;
            return;
        }

        // Backend workflow actions need a patient in most cases.
        const pid = this.order.patient && this.order.patient.id;
        if (action.needs_patient && !pid) {
            this.notification.add("Select or register a patient first.", { type: "warning" });
            this.openPatientModal();
            return;
        }
        if (!this.action) {
            this.notification.add("This action is not available here.", { type: "danger" });
            return;
        }

        const ctx = {};
        if (pid) {
            ctx.default_patient_id = pid;
        }
        if (this.order.doctor && this.order.doctor.id) {
            ctx.default_doctor_id = this.order.doctor.id;
        }

        let act;
        if (action.mode === "list") {
            // NB: Odoo 17 list view type token is 'tree' (not 'list').
            // Only filter by patient on models that are patient-scoped.
            const domain = (action.needs_patient && pid) ? [["patient_id", "=", pid]] : [];
            act = {
                type: "ir.actions.act_window",
                name: action.label,
                res_model: action.model,
                views: [[false, "tree"], [false, "form"]],
                domain: domain,
                context: ctx,
                target: "current",
            };
        } else {
            act = {
                type: "ir.actions.act_window",
                name: action.label,
                res_model: action.model,
                views: [[false, "form"]],
                context: ctx,
                target: "new",
            };
        }
        this.action.doAction(act);
    }

    async createPatient() {
        if (!this.newPatient.name.trim()) {
            this.notification.add("Please enter a patient name.", { type: "warning" });
            return;
        }
        try {
            const patient = await this.orm.call(
                "healthcare.pos.order", "create_patient_from_ui", [{ ...this.newPatient }]);
            this.patients.unshift(patient);
            this.selectPatient(patient);
            this.notification.add(`Patient "${patient.name}" created.`, { type: "success" });
        } catch (e) {
            const msg = (e && e.message && e.message.data && e.message.data.message) || "Could not create patient.";
            this.notification.add(msg, { type: "danger" });
        }
    }

    setDoctor(doctorId) {
        const id = parseInt(doctorId, 10);
        this.order.doctor = this.doctors.find((d) => d.id === id) || null;
    }

    // ------------------------------------------------------------------
    // Payment
    // ------------------------------------------------------------------
    get amountPaid() {
        return this.payments.reduce((s, p) => s + (Number(p.amount) || 0), 0);
    }
    get amountDue() {
        return this.amountTotal - this.amountPaid;
    }
    get changeDue() {
        const diff = this.amountPaid - this.amountTotal;
        return diff > 0 ? diff : 0;
    }

    goToPayment() {
        if (!this.order.lines.length) {
            this.notification.add("Add at least one service to the order.", { type: "warning" });
            return;
        }
        if (this.config.require_patient && !this.order.patient) {
            this.notification.add("Select or create a patient first.", { type: "warning" });
            this.openPatientModal();
            return;
        }
        this.payments = [];
        this.screen = "payment";
    }

    addPayment(method) {
        const remaining = Math.max(0, this.amountDue);
        this.payments.push({
            methodId: method.id,
            name: method.name,
            isCash: method.is_cash,
            amount: Number(remaining.toFixed(this.currency.decimals)),
        });
    }
    removePayment(index) {
        this.payments.splice(index, 1);
    }

    async validateOrder() {
        if (this.amountPaid + 1e-6 < this.amountTotal) {
            this.notification.add("The amount paid is less than the total due.", { type: "warning" });
            return;
        }
        const payload = {
            session_id: this.session.id,
            patient_id: this.order.patient ? this.order.patient.id : false,
            doctor_id: this.order.doctor ? this.order.doctor.id : false,
            note: this.order.note || "",
            lines: this.order.lines.map((l) => ({
                service_id: l.serviceId,
                qty: Number(l.qty) || 0,
                price_unit: Number(l.priceUnit) || 0,
                discount: Number(l.discount) || 0,
                tax_percent: Number(l.taxPercent) || 0,
            })),
            payments: this.payments.map((p) => ({
                payment_method_id: p.methodId,
                amount: Number(p.amount) || 0,
                is_cash: p.isCash,
            })),
        };
        try {
            this.receipt = await this.orm.call(
                "healthcare.pos.order", "settle_order_from_ui", [payload]);
            this.screen = "receipt";
        } catch (e) {
            const msg = (e && e.message && e.message.data && e.message.data.message) || "Could not validate the order.";
            this.notification.add(msg, { type: "danger" });
        }
    }

    newOrder() {
        this.order = this._emptyOrder();
        this.payments = [];
        this.receipt = null;
        this.screen = "product";
        this.searchTerm = "";
    }

    // ------------------------------------------------------------------
    // Formatting
    // ------------------------------------------------------------------
    fmt(value) {
        const n = Number(value || 0).toLocaleString(undefined, {
            minimumFractionDigits: this.currency.decimals,
            maximumFractionDigits: this.currency.decimals,
        });
        return this.currency.position === "after"
            ? `${n} ${this.currency.symbol}`
            : `${this.currency.symbol} ${n}`;
    }
}

export function makePosStore(orm, notification, action) {
    return reactive(new PosStore(orm, notification, action));
}
