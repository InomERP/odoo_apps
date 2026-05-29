/** @odoo-module **/
/**
 * LotSelectionPopup — final (Phases 2 + 3 + 4)
 * ─────────────────────────────────────────────────────────────────────
 * Owl.js popup for picking Lot/Serial numbers, with:
 *   Phase 2: searchable list, manual entry, debounced autocomplete,
 *            tracking-mode aware, keyboard/mouse/touch, safe cancel.
 *   Phase 3: strict per-lot qty validation against stock.lot.product_qty,
 *            serial mode → qty forced to 1, lot mode → multi-qty.
 *   Phase 4: real-time available-qty (decremented by lots already chosen
 *            on other lines of the current order), unknown-lot prompt,
 *            duplicate-serial detection (in-order + historical),
 *            in-popup "Create new lot" form (group-gated by Phase 1).
 */
import { useState, useRef, onMounted } from "@odoo/owl";
import { AbstractAwaitablePopup } from "@point_of_sale/app/popup/abstract_awaitable_popup";
import { useService } from "@web/core/utils/hooks";
import { debounce } from "@web/core/utils/timing";
import { _t } from "@web/core/l10n/translation";


export class LotSelectionPopup extends AbstractAwaitablePopup {
    static template = "inom_pos_product_by_lot_number.LotSelectionPopup";
    // static props = {
    //     product:        { type: Object },
    //     cachedLots:     { type: Array,    optional: true },
    //     initialLots:    { type: Array,    optional: true },
    //     usedInOrder:    { type: Object,   optional: true },
    // };

    static props = {
        product:        { type: Object },
        cachedLots:     { type: Array,    optional: true },
        initialLots:    { type: Array,    optional: true },
        usedInOrder:    { type: Object,   optional: true },
        // Odoo 17 popup service extra props
        zIndex:         { type: Number,   optional: true },
        cancelKey:      { type: String,   optional: true },
        confirmKey:     { type: String,   optional: true },
        id:             { type: Number,   optional: true },
        resolve:        { type: Function, optional: true },
        close:          { type: Function, optional: true },
    };






    static defaultProps = {
        cachedLots:  [],
        initialLots: [],
        usedInOrder: {},
    };

    // ─────────────────────────────────────────────────────────────────
    setup() {
        super.setup(...arguments);
        this.orm = useService("orm");
        this.notification = useService("notification");
        try { this.pos = useService("pos"); } catch (e) { this.pos = null; }

        this.tracking = this.props.product.tracking || "lot";
        this.isSerial = this.tracking === "serial";

        this.state = useState({
            searchTerm: "",
            availableLots: [],
            // Map<lot_name, qty>
            selected: new Map(),
            // Map<lot_name, error string> — for inline error display
            errors: new Map(),
            highlightIndex: -1,
            loading: false,
            firstLoadDone: false,
            // Phase 4 — Create lot inline form
            showCreateForm: false,
            createName: "",
            createRef: "",
            creating: false,
        });

        this.searchInputRef = useRef("searchInput");
        this._resolved = false;
        this._seedFromPropsAndCache();

        this._debouncedAutocomplete = debounce(
            this._runRemoteAutocomplete.bind(this), 300,
        );

        onMounted(async () => {
            await this._refreshFromBackend();
            this.searchInputRef.el?.focus();
        });

        // onMounted(() => {
        //     this._refreshFromBackend();
        //     this.searchInputRef.el?.focus();
        // });

    }

    // ─────────────────────────────────────────────────────────────────
    // DATA
    // ─────────────────────────────────────────────────────────────────

    _seedFromPropsAndCache() {
        const byName = new Map();
        for (const lot of this.props.cachedLots) {
            if (lot?.name) byName.set(lot.name, lot);
        }
        this.state.availableLots = Array.from(byName.values());
        for (const existing of this.props.initialLots) {
            const name = existing.lot_name || existing.name;
            if (name) this.state.selected.set(name, existing.qty || 1);
        }
    }

    // async _refreshFromBackend() {
    //     this.state.loading = true;
    //     try {
    //         const fresh = await this.orm.call(
    //             "stock.lot",
    //             "get_lots_by_product",
    //             [this.props.product.id],
    //         );
    //         const merged = new Map();
    //         for (const l of this.state.availableLots) merged.set(l.name, l);
    //         for (const l of fresh)                    merged.set(l.name, l);
    //         this.state.availableLots = Array.from(merged.values());
    //     } catch (err) {
    //         // Offline-tolerant: stick with cache
    //         console.warn("[iml_pos_lot] refresh failed, using cache:", err);
    //     } finally {
    //         this.state.loading = false;
    //         this.state.firstLoadDone = true;
    //     }
    // }



    async _refreshFromBackend() {
        this.state.loading = true;
        try {
            const fresh = await this.orm.call(
                "stock.lot",
                "get_lots_by_product",
                [this.props.product.id],
            );
            // Fresh data se replace karo — cache merge nahi
            if (fresh && fresh.length >= 0) {
                this.state.availableLots = fresh;
            }
        } catch (err) {
            // Offline: cache rakhte hain
            console.warn("[iml_pos_lot] refresh failed, using cache:", err);
        } finally {
            this.state.loading = false;
            this.state.firstLoadDone = true;
        }
    }






    // ─────────────────────────────────────────────────────────────────
    // PHASE 4 — Real-time remaining qty per lot
    // ─────────────────────────────────────────────────────────────────

    /**
     * Effective qty available for this lot = product_qty
     *   - qty already used by other lines of the current order
     */
    // effectiveAvailable(lot) {
    //     const baseQty = Number(lot.product_qty) || 0;
    //     const usedElsewhere = Number(this.props.usedInOrder[lot.name]) || 0;
    //     return Math.max(0, baseQty - usedElsewhere);
    // }


    effectiveAvailable(lot) {
        const baseQty = Number(lot.product_qty) || 0;

        // Real-time: pos store se live recalculate karo
        let usedElsewhere = 0;
        try {
            const pos = this.pos;
            if (pos && typeof pos._iml_collectUsedQtyForProduct === "function") {
                const liveUsed = pos._iml_collectUsedQtyForProduct(this.props.product);
                usedElsewhere = Number(liveUsed[lot.name]) || 0;
            } else {
                usedElsewhere = Number(this.props.usedInOrder[lot.name]) || 0;
            }
        } catch (e) {
            usedElsewhere = Number(this.props.usedInOrder[lot.name]) || 0;
        }

        return Math.max(0, baseQty - usedElsewhere);
    }





    // ─────────────────────────────────────────────────────────────────
    // CONFIG GETTERS
    // ─────────────────────────────────────────────────────────────────

    get minChars() {
        return Number(this.pos?.config?.iml_lot_autocomplete_min_chars) || 2;
    }
    get autocompleteLimit() {
        return Number(this.pos?.config?.iml_lot_autocomplete_limit) || 20;
    }
    get strictQty() {
        return !!this.pos?.config?.iml_strict_qty_validation;
    }
    get checkDuplicateSerial() {
        return !!this.pos?.config?.iml_check_duplicate_serial;
    }
    get canCreateLot() {
        return !!this.pos?.config?.iml_allow_create_lot;
    }

    // ─────────────────────────────────────────────────────────────────
    // FILTER / AUTOCOMPLETE
    // ─────────────────────────────────────────────────────────────────

    get displayedLots() {
        const term = this.state.searchTerm.trim().toLowerCase();
        if (!term) return this.state.availableLots;
        return this.state.availableLots.filter(l =>
            (l.name || "").toLowerCase().includes(term),
        );
    }

    get typedTermIsNovel() {
        const term = this.state.searchTerm.trim();
        if (!term) return false;
        return !this.state.availableLots.some(l => l.name === term);
    }

    onSearchInput(ev) {
        this.state.searchTerm = ev.target.value;
        this.state.highlightIndex = -1;
        if (this.state.searchTerm.trim().length >= this.minChars) {
            this._debouncedAutocomplete();
        }
    }

    async _runRemoteAutocomplete() {
        const term = this.state.searchTerm.trim();
        if (!term) return;
        try {
            const results = await this.orm.call(
                "stock.lot",
                "search_lots_autocomplete",
                [term, this.props.product.id, this.autocompleteLimit],
            );
            const known = new Set(this.state.availableLots.map(l => l.name));
            for (const r of results) {
                if (!known.has(r.name)) this.state.availableLots.push(r);
            }
        } catch (err) {
            // Silent — local list still works
        }
    }

    // ─────────────────────────────────────────────────────────────────
    // SELECTION
    // ─────────────────────────────────────────────────────────────────

    isSelected(lotName) { return this.state.selected.has(lotName); }
    qtyFor(lotName)    { return this.state.selected.get(lotName) || 0; }
    errorFor(lotName)  { return this.state.errors.get(lotName) || ""; }

    toggleLot(lot) {
        const name = lot.name;
        if (!name) return;

        if (this.state.selected.has(name)) {
            this.state.selected.delete(name);
            this.state.errors.delete(name);
            return;
        }
        if (this.isSerial) this.state.selected.clear();

        // Phase 3: zero-stock + strict-qty short-circuit
        if (this.strictQty && !lot._isManual) {
            const eff = this.effectiveAvailable(lot);
            if (eff <= 0 && !this.isSerial) {
                this.notification.add(
                    _t("This lot has no remaining stock."),
                    { type: "warning" },
                );
                return;
            }
        }
        this.state.selected.set(name, 1);
        this.state.errors.delete(name);

        // Phase 4: duplicate-serial pre-check on selection
        if (this.isSerial) this._validateSerialAsync(name);
    }

    /**
     * Per-row qty change with strict cap (Phase 3).
     */
    onQtyChange(lotName, ev) {
        let qty = parseFloat(ev.target.value);
        if (isNaN(qty) || qty < 0) qty = 0;
        if (this.isSerial) qty = qty > 0 ? 1 : 0;

        const lot = this.state.availableLots.find(l => l.name === lotName);

        if (this.strictQty && lot && !lot._isManual && !this.isSerial) {
            const max = this.effectiveAvailable(lot);
            if (qty > max) {
                this.state.errors.set(
                    lotName,
                    _t("Max available: %(n)s", { n: max }),
                );
                qty = max;
                // Visually sync the input
                if (ev.target) ev.target.value = qty;
            } else {
                this.state.errors.delete(lotName);
            }
        }

        if (qty === 0) {
            this.state.selected.delete(lotName);
            this.state.errors.delete(lotName);
        } else {
            this.state.selected.set(lotName, qty);
        }
    }

    // ─────────────────────────────────────────────────────────────────
    // PHASE 4 — Unknown lot manual entry
    // ─────────────────────────────────────────────────────────────────

    async addManualEntry() {
        const name = this.state.searchTerm.trim();
        if (!name) return;

        const isKnown = this.state.availableLots.some(l => l.name === name);

        // Phase 4: unknown lot → offer to create
        if (!isKnown && this.canCreateLot) {
            this.state.createName = name;
            this.state.createRef = "";
            this.state.showCreateForm = true;
            return;
        }

        // Otherwise add as a manual entry
        if (!isKnown) {
            this.state.availableLots.push({
                id: `manual-${name}`,
                name,
                product_qty: 0,
                expiration_date: false,
                _isManual: true,
            });
        }
        if (this.isSerial) this.state.selected.clear();
        this.state.selected.set(name, 1);
        if (this.isSerial) this._validateSerialAsync(name);
        this.state.searchTerm = "";
        this.searchInputRef.el?.focus();
    }

    // ─────────────────────────────────────────────────────────────────
    // PHASE 4 — Create lot inline form
    // ─────────────────────────────────────────────────────────────────

    openCreateForm() {
        this.state.createName = this.state.searchTerm.trim();
        this.state.createRef = "";
        this.state.showCreateForm = true;
    }
    closeCreateForm() {
        this.state.showCreateForm = false;
        this.state.createName = "";
        this.state.createRef = "";
    }
    onCreateNameInput(ev)  { this.state.createName = ev.target.value; }
    onCreateRefInput(ev)   { this.state.createRef  = ev.target.value; }

    async submitCreateLot() {
        const name = this.state.createName.trim();
        if (!name) {
            this.notification.add(_t("Lot name is required."), { type: "warning" });
            return;
        }
        this.state.creating = true;
        try {
            // Offline-aware: pos_store exposes a helper that auto-queues when offline
            const result = await this.pos.iml_createLotFromPos({
                name,
                product_id: this.props.product.id,
                ref: this.state.createRef.trim() || undefined,
            });

            if (!result || !result.name) {
                throw new Error(_t("Lot creation returned no result."));
            }

            // Merge into available list
            if (!this.state.availableLots.some(l => l.name === result.name)) {
                this.state.availableLots.push({
                    id: result.id,
                    name: result.name,
                    product_qty: result.product_qty || 0,
                    expiration_date: result.expiration_date || false,
                });
            }
            if (this.isSerial) this.state.selected.clear();
            this.state.selected.set(result.name, 1);

            this.notification.add(
                result.queued
                    ? _t("Lot queued for sync (offline).")
                    : result.duplicate
                        ? _t("Lot already existed; selected.")
                        : _t("Lot created and selected."),
                { type: result.queued ? "info" : result.duplicate ? "warning" : "success" },
            );

            this.state.searchTerm = "";
            this.closeCreateForm();
            this.searchInputRef.el?.focus();
        } catch (err) {
            const msg = err?.data?.message || err?.message || _t("Failed to create lot.");
            this.notification.add(msg, { type: "danger" });
        } finally {
            this.state.creating = false;
        }
    }

    // ─────────────────────────────────────────────────────────────────
    // PHASE 4 — Duplicate-serial check
    // ─────────────────────────────────────────────────────────────────

    async _validateSerialAsync(lotName) {
        if (!this.isSerial || !this.checkDuplicateSerial) return;

        // (a) Current order: any other line using this serial?
        const usedHere = Number(this.props.usedInOrder[lotName]) || 0;
        if (usedHere > 0) {
            this.state.errors.set(
                lotName,
                _t("Serial '%(n)s' is already used in this order.", { n: lotName }),
            );
            return;
        }

        // (b) Historical: ask the backend
        try {
            const used = await this.orm.call(
                "stock.lot", "check_serial_used",
                [lotName, this.props.product.id],
            );
            if (used) {
                this.state.errors.set(
                    lotName,
                    _t("Serial '%(n)s' has already been sold.", { n: lotName }),
                );
            }
        } catch (err) {
            // Offline: skip historical check; in-order check is enough
        }
    }

    // ─────────────────────────────────────────────────────────────────
    // KEYBOARD
    // ─────────────────────────────────────────────────────────────────

    onKeyDown(ev) {
        const rows = this.displayedLots;
        if (ev.key === "ArrowDown" && rows.length) {
            ev.preventDefault();
            this.state.highlightIndex = (this.state.highlightIndex + 1) % rows.length;
        } else if (ev.key === "ArrowUp" && rows.length) {
            ev.preventDefault();
            this.state.highlightIndex =
                (this.state.highlightIndex - 1 + rows.length) % rows.length;
        } else if (ev.key === "Enter") {
            ev.preventDefault();
            const i = this.state.highlightIndex;
            if (i >= 0 && rows[i]) {
                this.toggleLot(rows[i]);
            } else if (this.typedTermIsNovel) {
                this.addManualEntry();
            } else if (rows.length === 1) {
                this.toggleLot(rows[0]);
            }
        } else if (ev.key === "Escape") {
            ev.preventDefault();
            if (this.state.showCreateForm) this.closeCreateForm();
            else this.cancel();
        }
    }

    // ─────────────────────────────────────────────────────────────────
    // CONFIRM / CANCEL
    // ─────────────────────────────────────────────────────────────────

    get totalSelectedQty() {
        let t = 0;
        for (const q of this.state.selected.values()) t += q;
        return t;
    }
    get hasErrors() {
        return this.state.errors.size > 0;
    }
    get canConfirm() {
        return this.state.selected.size > 0
            && this.totalSelectedQty > 0
            && !this.hasErrors
            && !this.state.showCreateForm;
    }
    get title() {
        const label = this.isSerial
            ? _t("Select Serial Number")
            : _t("Select Lot Number(s)");
        return `${label} — ${this.props.product.display_name || this.props.product.name || ""}`;
    }
    get trackingLabel() {
        return this.isSerial ? _t("By Serial") : _t("By Lot");
    }

    async confirm() {
        if (!this.canConfirm) {
            return;
        }
        // Final pass: validate every selected serial against duplicates
        if (this.isSerial && this.checkDuplicateSerial) {
            const checks = [...this.state.selected.keys()].map((n) => this._validateSerialAsync(n));
            await Promise.all(checks);
            if (this.hasErrors) {
                return;
            }
        }
        // AbstractAwaitablePopup.confirm() calls getPayload() and closes.
        await super.confirm();
    }

    // Payload consumed by PosStore.getEditedPackLotLines (Odoo 17).
    async getPayload() {
        const lots = [];
        for (const [name, qty] of this.state.selected.entries()) {
            lots.push({ lot_name: name, qty });
        }
        return { lots, totalQty: this.totalSelectedQty };
    }
    // cancel() inherited from AbstractAwaitablePopup -> {confirmed:false, payload:null}
}
