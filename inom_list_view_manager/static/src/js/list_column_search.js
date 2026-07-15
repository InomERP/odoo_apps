/** @odoo-module **/

import { ListRenderer } from "@web/views/list/list_renderer";
import { patch } from "@web/core/utils/patch";
import { onMounted, onPatched } from "@odoo/owl";


const M2X_FIELDS = [
    "salesperson", "user_id", "partner_id", "customer",
    "sales_team_id", "team_id", "company_id", "tag_ids",
    "categ_ids", "tags", "category"
];

patch(ListRenderer.prototype, {
    setup() {
        super.setup(...arguments);
        this._advancedFiltersByIndex = {};
        this._m2xSelectedByIndex = {};
        onMounted(() => this._tryInitFilterRow());
        onPatched(() => this._tryInitFilterRow());
    },

    _tryInitFilterRow(attempt = 1) {
        const table = document.querySelector(".o_list_renderer table");
        const thead = table ? table.querySelector("thead") : null;
        if (table && thead) {
            this._ensureAdvancedFilterRow();
            this._applyAdvancedFilters();
        } else if (attempt < 10) {
            setTimeout(() => this._tryInitFilterRow(attempt + 1), 200);
        }
    },

    _getLabelForHeaderCell(headerCell) {
        const fieldName = headerCell.dataset.name || "";
        if (fieldName && Array.isArray(this.columns) && this.columns.length) {
            const col = this.columns.find((c) => c.name === fieldName);
            if (col) {
                const lbl = (col.label || col.string || "").trim();
                if (lbl) return lbl;
            }
        }
        const clone = headerCell.cloneNode(true);
        clone.querySelectorAll("i, .o_resize, button, input, [class*='fa']").forEach((el) => el.remove());
        for (const span of clone.querySelectorAll("span")) {
            const txt = span.textContent.trim();
            if (txt) return txt;
        }
        return clone.textContent.trim();
    },

    _isM2xField(fieldName) {
        if (!fieldName) return false;
        return M2X_FIELDS.some((f) => fieldName.toLowerCase().includes(f.toLowerCase()));
    },

    _getUniqueValuesForColumn(colIndex) {
        const table = document.querySelector(".o_list_renderer table");
        if (!table) return [];
        const rows = table.querySelectorAll("tbody tr.o_data_row");
        const seen = new Set();
        rows.forEach((row) => {
            const cell = row.querySelectorAll("td")[colIndex];
            const txt = (cell?.textContent || "").trim();
            if (txt) seen.add(txt);
        });
        return Array.from(seen).sort();
    },

    _ensureAdvancedFilterRow() {
        const table = document.querySelector(".o_list_renderer table");
        const thead = table ? table.querySelector("thead") : null;
        if (!thead) return;

        const headerRow = thead.querySelector("tr");
        if (!headerRow) return;

        const previous = thead.querySelector("tr.o_advanced_filter_row");
        if (previous) previous.remove();

        const headerCells = Array.from(headerRow.querySelectorAll("th"));
        if (!headerCells.length) return;

        const filterRow = document.createElement("tr");
        filterRow.className = "o_advanced_filter_row";

        headerCells.forEach((headerCell, index) => {
            const th = document.createElement("th");
            th.style.padding = "2px 4px";
            th.style.position = "relative";

            const fieldName = headerCell.dataset.name || "";
            const label = this._getLabelForHeaderCell(headerCell);

            if (fieldName || label) {
                if (this._isM2xField(fieldName)) {
                    // ── M2x Tag Style ──
                    this._buildM2xCell(th, index, label, fieldName);
                } else {
                    // ── Simple text input ──
                    const input = document.createElement("input");
                    input.type = "text";
                    input.className = "form-control form-control-sm";
                    input.style.cssText = "font-size:11px;height:24px;padding:2px 4px;min-width:0;";
                    input.placeholder = label || fieldName || "Search...";
                    input.title = label || fieldName || "Search...";
                    input.value = this._advancedFiltersByIndex[index] || "";

                    input.addEventListener("input", (ev) => {
                        this._advancedFiltersByIndex[index] = ev.target.value || "";
                        this._applyAdvancedFilters();
                    });
                    input.addEventListener("keydown", (ev) => {
                        if (ev.key === "Escape") {
                            ev.target.value = "";
                            this._advancedFiltersByIndex[index] = "";
                            this._applyAdvancedFilters();
                        }
                    });
                    th.appendChild(input);
                }
            }

            filterRow.appendChild(th);
        });

        headerRow.insertAdjacentElement("afterend", filterRow);
    },

    _buildM2xCell(th, index, label, fieldName) {
        if (!this._m2xSelectedByIndex[index]) {
            this._m2xSelectedByIndex[index] = new Set();
        }
        const selectedTags = this._m2xSelectedByIndex[index];

        // ── Wrapper ──
        const wrapper = document.createElement("div");
        wrapper.style.cssText = `
            position: relative;
            min-width: 80px;
        `;

        // ── Tag + Input Box ──
        const tagBox = document.createElement("div");
        tagBox.style.cssText = `
            display: flex;
            flex-wrap: wrap;
            align-items: center;
            gap: 3px;
            min-height: 26px;
            border: 1px solid #ced4da;
            border-radius: 4px;
            padding: 2px 4px;
            background: #fff;
            cursor: text;
            font-size: 11px;
        `;

        // ── Dropdown ──
        const dropdown = document.createElement("div");
        dropdown.style.cssText = `
            display: none;
            position: absolute;
            top: 100%;
            left: 0;
            min-width: 180px;
            max-height: 200px;
            overflow-y: auto;
            background: #fff;
            border: 1px solid #ddd;
            border-radius: 6px;
            box-shadow: 0 4px 16px rgba(0,0,0,0.13);
            z-index: 9999;
        `;

        // ── Search input inside tagBox ──
        const searchInput = document.createElement("input");
        searchInput.type = "text";
        searchInput.placeholder = label;
        searchInput.style.cssText = `
            border: none;
            outline: none;
            font-size: 11px;
            flex: 1;
            min-width: 40px;
            height: 20px;
            padding: 0;
            background: transparent;
        `;

        const renderTags = () => {
            // Purane chips hata do (input ke alawa)
            Array.from(tagBox.children).forEach((c) => {
                if (c !== searchInput) c.remove();
            });

            selectedTags.forEach((val) => {
                const chip = document.createElement("span");
                chip.style.cssText = `
                    display: inline-flex;
                    align-items: center;
                    gap: 3px;
                    background: #7c3aed;
                    color: #fff;
                    border-radius: 10px;
                    padding: 1px 7px;
                    font-size: 10px;
                    font-weight: 500;
                    white-space: nowrap;
                `;
                chip.innerHTML = `${val} <span style="cursor:pointer;font-size:11px;line-height:1;">✕</span>`;
                chip.querySelector("span").onclick = (e) => {
                    e.stopPropagation();
                    selectedTags.delete(val);
                    renderTags();
                    renderDropdown(searchInput.value);
                    this._applyAdvancedFilters();
                };
                tagBox.insertBefore(chip, searchInput);
            });
        };

        const renderDropdown = (query = "") => {
            dropdown.innerHTML = "";
            const q = query.trim().toLowerCase();
            const uniqueValues = this._getUniqueValuesForColumn(index);
            const filtered = uniqueValues.filter(
                (v) => !selectedTags.has(v) && (!q || v.toLowerCase().includes(q))
            );

            if (!filtered.length) {
                const empty = document.createElement("div");
                empty.style.cssText = "padding:8px 12px;font-size:12px;color:#aaa;text-align:center;";
                empty.textContent = "No values found";
                dropdown.appendChild(empty);
                return;
            }

            filtered.forEach((val) => {
                const item = document.createElement("div");
                item.textContent = val;
                item.style.cssText = `
                    padding: 6px 12px;
                    font-size: 12px;
                    cursor: pointer;
                    border-bottom: 1px solid #f5f5f5;
                `;
                item.onmouseenter = () => (item.style.background = "#f3f0ff");
                item.onmouseleave = () => (item.style.background = "");
                item.onmousedown = (e) => {
                    e.preventDefault();
                    selectedTags.add(val);
                    searchInput.value = "";
                    renderTags();
                    renderDropdown("");
                    this._applyAdvancedFilters();
                };
                dropdown.appendChild(item);
            });
        };

        // ── Events ──
        searchInput.addEventListener("focus", () => {
            tagBox.style.borderColor = "#7c3aed";
            renderDropdown(searchInput.value);
            dropdown.style.display = "block";
        });

        searchInput.addEventListener("blur", () => {
            tagBox.style.borderColor = "#ced4da";
            setTimeout(() => (dropdown.style.display = "none"), 180);
        });

        searchInput.addEventListener("input", (e) => {
            renderDropdown(e.target.value);
            dropdown.style.display = "block";
        });

        searchInput.addEventListener("keydown", (e) => {
            if (e.key === "Escape") {
                selectedTags.clear();
                searchInput.value = "";
                renderTags();
                dropdown.style.display = "none";
                this._applyAdvancedFilters();
            }
        });

        tagBox.addEventListener("click", () => searchInput.focus());

        tagBox.appendChild(searchInput);
        wrapper.appendChild(tagBox);
        wrapper.appendChild(dropdown);
        th.appendChild(wrapper);

        renderTags();
    },

    // True only when at least one column text box has text OR at least one m2x
    // column has a selected tag. Used to decide whether the DOM-level row/group
    // hiding pass should run at all.
    _inomHasActiveAdvancedFilter() {
        const textActive = Object.values(this._advancedFiltersByIndex || {}).some(
            (v) => (v || "").trim() !== ""
        );
        if (textActive) return true;
        const m2xActive = Object.values(this._m2xSelectedByIndex || {}).some(
            (s) => s && s.size > 0
        );
        return m2xActive;
    },

    _applyAdvancedFilters() {
        const table = document.querySelector(".o_list_renderer table");
        if (!table) return;

        // ─────────────────────────────────────────────────────────────────────
        // ROOT-CAUSE FIX (Group By went blank).
        //
        // This method runs on every onMounted/onPatched via _tryInitFilterRow.
        // When NO per-column filter is active we must NOT touch row or group
        // visibility at all. In grouped mode Odoo renders groups collapsed:
        // the DOM has only `tr.o_group_header` rows and NO `tr.o_data_row`
        // rows until a group is expanded. The old group-header pass walked each
        // header's siblings, found no visible data rows (there are none while
        // collapsed), and set every group header to display:none — blanking the
        // whole list the instant Group By was applied.
        //
        // So: when no filter is active, clear any leftover display:none we may
        // have set on a previous pass and return, leaving native rendering
        // (flat OR grouped) completely untouched.
        // ─────────────────────────────────────────────────────────────────────
        if (!this._inomHasActiveAdvancedFilter()) {
            table.querySelectorAll("tbody tr.o_data_row").forEach((r) => {
                if (r.style.display === "none") r.style.display = "";
            });
            table.querySelectorAll("tbody tr.o_group_header").forEach((r) => {
                if (r.style.display === "none") r.style.display = "";
            });
            return;
        }

        const rows = table.querySelectorAll("tbody tr.o_data_row");
        rows.forEach((row) => {
            const cells = row.querySelectorAll("td");
            let show = true;

            // Text filters
            for (const [index, raw] of Object.entries(this._advancedFiltersByIndex)) {
                const val = (raw || "").trim().toLowerCase();
                if (!val) continue;
                const cellText = (cells[Number(index)]?.textContent || "").trim().toLowerCase();
                if (!cellText.includes(val)) { show = false; break; }
            }

            // M2x tag filters
            if (show) {
                for (const [index, tagSet] of Object.entries(this._m2xSelectedByIndex)) {
                    if (!tagSet || tagSet.size === 0) continue;
                    const cellText = (cells[Number(index)]?.textContent || "").trim();
                    const matches = Array.from(tagSet).some((t) =>
                        cellText.toLowerCase().includes(t.toLowerCase())
                    );
                    if (!matches) { show = false; break; }
                }
            }

            row.style.display = show ? "" : "none";
        });

        // Group headers (only reached when a filter IS active).
        //
        // A COLLAPSED group has no data rows rendered in the DOM. We must NEVER
        // hide it just because we can't see its (unrendered) children, or the
        // grouped list goes blank. We therefore hide a group header ONLY when it
        // is expanded (has data rows in the DOM) AND every one of those rows is
        // filtered out. Collapsed groups always stay visible.
        table.querySelectorAll("tbody tr.o_group_header").forEach((groupRow) => {
            let sib = groupRow.nextElementSibling;
            let hasDataRow = false;
            let hasVisible = false;
            while (sib && !sib.classList.contains("o_group_header")) {
                if (sib.classList.contains("o_data_row")) {
                    hasDataRow = true;
                    if (sib.style.display !== "none") hasVisible = true;
                }
                sib = sib.nextElementSibling;
            }
            // Expanded + all children filtered out -> hide. Otherwise show.
            groupRow.style.display = (hasDataRow && !hasVisible) ? "none" : "";
        });
    },
});