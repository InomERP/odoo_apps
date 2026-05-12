/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ListRenderer } from "@web/views/list/list_renderer";
import { useService } from "@web/core/utils/hooks";
import { onMounted, onPatched } from "@odoo/owl";

/**
 * Adds an eye-icon column to every list view by injecting cells into
 * the rendered DOM.
 *
 * Key design point: the eye BUTTON is always emitted, regardless of
 * whether we can find the matching record at injection time. The record
 * is resolved at *click* time. This handles list views whose data isn't
 * available on `this.props.list.records` at the moment we first render
 * (custom subclasses like the account.move list renderer, lazy-loaded
 * group contents, etc.).
 *
 * Three layers of resilience guarantee the column stays visible:
 *
 *   1. onMounted    — first injection on initial mount.
 *   2. onPatched    — re-injection after every OWL re-render.
 *   3. MutationObserver(subtree: true, filtered) — catches rows added
 *      asynchronously, e.g. after expanding a group, applying a filter,
 *      or any custom rendering path.
 */
patch(ListRenderer.prototype, {
    setup() {
        super.setup();
        this.recordDrawer = useService("record_drawer");

        const inject = () => this._qfdInject();
        onMounted(inject);
        onPatched(inject);
    },

    _qfdInject() {
        const tables = document.querySelectorAll(".o_list_table");
        for (const table of tables) {
            this._qfdInjectIntoTable(table);
        }
    },

    _qfdInjectIntoTable(table) {
        this._qfdInjectHeader(table);
        this._qfdInjectRows(table);
        this._qfdSetupTableHandlers(table);
    },

    _qfdInjectHeader(table) {
        const headerRow = table.querySelector("thead > tr");
        if (!headerRow) return;
        if (headerRow.querySelector(".o_list_record_eye_header")) return;
        const th = document.createElement("th");
        th.className = "o_list_record_eye_header";
        th.setAttribute("tabindex", "-1");
        headerRow.appendChild(th);
    },

    _qfdInjectRows(table) {
        const dataRows = table.querySelectorAll("tbody tr.o_data_row");
        for (const row of dataRows) {
            if (row.querySelector(".o_list_record_eye_cell")) continue;
            this._qfdAddEyeCell(row);
        }
    },

    _qfdAddEyeCell(row) {
    const td = document.createElement("td");
    td.className = "o_list_record_eye_cell";

    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "btn btn-link o_list_record_eye_btn";
    btn.title = "Quick view";
    btn.setAttribute("tabindex", "-1");
    btn.innerHTML = `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>`;
    td.appendChild(btn);

    row.appendChild(td);
},

    _qfdSetupTableHandlers(table) {
        const tbody = table.querySelector("tbody");
        if (!tbody) return;
        if (tbody.dataset.qfdHandled) return;
        tbody.dataset.qfdHandled = "1";

        // Delegated click handler in capture mode so it fires before
        // Odoo's row-level click handler.
        tbody.addEventListener(
            "click",
            (ev) => {
                const btn = ev.target.closest(".o_list_record_eye_btn");
                if (!btn) return;
                ev.stopPropagation();
                ev.stopImmediatePropagation();
                ev.preventDefault();

                const row = btn.closest("tr.o_data_row");
                if (!row) return;

                const resolved = this._qfdResolveRecordForRow(row);
                if (resolved) {
                    this.recordDrawer.open(resolved.resModel, resolved.resId);
                } else {
                    // eslint-disable-next-line no-console
                    console.warn(
                        "[QuickFormDrawer] could not resolve record for clicked row"
                    );
                }
            },
            { capture: true }
        );

        // MutationObserver: subtree:true catches deeply-added rows
        // (lazy-loaded groups, custom rendering paths). Filtered to
        // only re-inject when the addition includes a real o_data_row,
        // so our own <td> additions never trigger us.
        const observer = new MutationObserver((mutations) => {
            let needsReinject = false;
            for (const m of mutations) {
                if (m.type !== "childList") continue;
                for (const node of m.addedNodes) {
                    if (node.nodeType !== Node.ELEMENT_NODE) continue;
                    if (
                        (node.classList && node.classList.contains("o_data_row")) ||
                        (node.querySelector && node.querySelector("tr.o_data_row"))
                    ) {
                        needsReinject = true;
                        break;
                    }
                }
                if (needsReinject) break;
            }
            if (needsReinject) {
                queueMicrotask(() => {
                    this._qfdInjectHeader(table);
                    this._qfdInjectRows(table);
                });
            }
        });
        observer.observe(tbody, { childList: true, subtree: true });
    },

    /**
     * Resolves the record for a given DOM row. Returns
     * { resModel, resId } or null.
     *
     * Strategy:
     *   1. Build a flat record list from the renderer's props.list,
     *      handling ungrouped + grouped + multi-level grouped.
     *   2. Find the row's index inside its tbody.
     *   3. Index into the flat list.
     */
    _qfdResolveRecordForRow(row) {
        const tbody = row.closest("tbody");
        if (!tbody) return null;
        const allRows = Array.from(tbody.querySelectorAll("tr.o_data_row"));
        const idx = allRows.indexOf(row);
        if (idx === -1) return null;

        const list = this.props && this.props.list;
        const records = this._qfdFlattenRecords(list);
        const record = records[idx];
        if (!record || !record.resId) return null;

        const resModel =
            record.resModel ||
            (list && list.resModel) ||
            (list && list.config && list.config.resModel) ||
            (list && list.model && list.model.config && list.model.config.resModel);

        if (!resModel) return null;
        return { resModel, resId: record.resId };
    },

    /**
     * Recursively walks a list datapoint to produce a flat array of
     * records in DOM order. Handles ungrouped lists, single-level
     * group_by, and multi-level group_by.
     */
    _qfdFlattenRecords(list) {
        if (!list) return [];

        // Ungrouped: list.records is the flat Record[].
        if (Array.isArray(list.records) && list.records.length) {
            const first = list.records[0];
            if (first && first.resId !== undefined) {
                return list.records;
            }
        }

        // Grouped: walk groups.
        if (Array.isArray(list.groups)) {
            const flat = [];
            for (const group of list.groups) {
                if (group.list) {
                    flat.push(...this._qfdFlattenRecords(group.list));
                } else if (Array.isArray(group.records)) {
                    flat.push(...group.records);
                }
            }
            return flat;
        }

        return Array.isArray(list.records) ? list.records : [];
    },
});
