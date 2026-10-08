/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ListRenderer } from "@web/views/list/list_renderer";

// Delay used to tell a single click apart from a double click.
const INOM_CLICK_DELAY = 250;

patch(ListRenderer.prototype, {

    setup() {
        super.setup(...arguments);
        // Pending single-click copy timer (cancelled if a double click follows).
        this._inomCopyTimer = null;
    },

    // ─────────────────────────────────────────────────────────────────────────
    // NEW BEHAVIOUR
    //   • SINGLE click on a data cell  -> copy that cell's value to clipboard.
    //   • DOUBLE click on a data cell  -> open the form view (Odoo default).
    //
    // We override the SAME hook Odoo uses to open a record on click
    // (onCellClicked -> this.props.openRecord). Single click schedules a copy
    // and does NOT call super (so the form does not open); a following double
    // click cancels that copy and opens the record. Every other situation
    // (editable lists, multi-edit, an active selection, noOpen lists, clicks on
    // buttons/links/inputs) falls through to Odoo's exact default behaviour, so
    // nothing existing breaks.
    // ─────────────────────────────────────────────────────────────────────────
    async onCellClicked(record, column, ev, newWindow) {
        const list = this.props.list;
        const hasSelection = !!(list && list.selection && list.selection.length);
        const target = ev && ev.target;

        const isInteractiveTarget =
            target &&
            target.closest(
                "button, a, input, textarea, select, label, .o-checkbox, .o_list_record_selector, .dropdown, .o_list_many2many_tags_cell .badge"
            );

        // Only take over the plain "open on single click" case.
        const isPlainOpenClick =
            !this.props.editable &&
            !hasSelection &&
            !this.props.archInfo?.noOpen &&
            !(this.isInlineEditable && this.isInlineEditable(record)) &&
            !isInteractiveTarget;

        if (!isPlainOpenClick) {
            return super.onCellClicked(record, column, ev, newWindow);
        }

        // DOUBLE click -> cancel the pending copy and open the form normally.
        if (ev.detail >= 2) {
            if (this._inomCopyTimer) {
                clearTimeout(this._inomCopyTimer);
                this._inomCopyTimer = null;
            }
            if (typeof this.props.openRecord === "function") {
                this.props.openRecord(record, { newWindow });
            }
            return;
        }

        // SINGLE click -> schedule a copy of THIS cell's value (suppress open).
        const cell =
            (target && target.closest("td.o_data_cell")) ||
            (ev && ev.currentTarget) ||
            null;
        const text = cell ? (cell.innerText || "").trim() : "";

        if (this._inomCopyTimer) {
            clearTimeout(this._inomCopyTimer);
        }
        this._inomCopyTimer = setTimeout(async () => {
            this._inomCopyTimer = null;
            if (!text) return;
            const ok = await this._inomCopyText(text);
            if (ok && cell) {
                this._inomFlashCopied(cell);
            }
        }, INOM_CLICK_DELAY);

        // NOTE: intentionally NOT calling super -> a single click does not open
        // the form.
    },

    // Brief, layout-safe visual confirmation that the value was copied.
    _inomFlashCopied(cell) {
        try {
            const prev = cell.style.backgroundColor;
            cell.style.transition = "background-color 0.15s ease";
            cell.style.backgroundColor = "rgba(40, 167, 69, 0.25)";
            setTimeout(() => {
                cell.style.backgroundColor = prev || "";
            }, 400);
        } catch (e) {
            // visual only — never let it affect behaviour
        }
    },

    // Clipboard write that also works on NON-secure contexts (http://<lan-ip>),
    // where navigator.clipboard is undefined.
    async _inomCopyText(text) {
        if (navigator.clipboard && window.isSecureContext) {
            try {
                await navigator.clipboard.writeText(text);
                return true;
            } catch (err) {
                // fall through to the legacy fallback below
            }
        }
        try {
            const ta = document.createElement("textarea");
            ta.value = text;
            ta.setAttribute("readonly", "");
            ta.style.position = "fixed";
            ta.style.top = "-1000px";
            ta.style.left = "-1000px";
            ta.style.opacity = "0";
            document.body.appendChild(ta);
            ta.focus();
            ta.select();
            const ok = document.execCommand("copy");
            document.body.removeChild(ta);
            return ok;
        } catch (err) {
            console.error("[Inom LVM] copy failed:", err);
            return false;
        }
    },
});