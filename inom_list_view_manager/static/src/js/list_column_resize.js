/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ListRenderer } from "@web/views/list/list_renderer";
import { onMounted, onPatched } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

patch(ListRenderer.prototype, {
    setup() {
        super.setup();

        this.inomService = useService("inom_list_view_manager");

        onMounted(async () => {
            await this._applySavedColumnWidths();
            this._inomApplyColumnOrderToDOM();
            await this._inomApplyHiddenColumns();
            await this._inomApplyColumnLabels();
            this._enableColumnResize();
        });

        onPatched(async () => {
            await this._applySavedColumnWidths();
            this._inomApplyColumnOrderToDOM();
            await this._inomApplyHiddenColumns();
            await this._inomApplyColumnLabels();
            this._enableColumnResize();
        });
    },

    // ─────────────────────────────────────────────────────────────────────────
    // FIX 1 — Hide / Show Columns
    // Reads config directly from DB (not cache) to avoid timing issues
    // ─────────────────────────────────────────────────────────────────────────
    async _inomApplyHiddenColumns() {
        try {
            const modelName = this.props.list?.resModel;
            const viewId    = this.props.archInfo?.viewId;
            if (!modelName) return;

            const config = await this.inomService.loadConfig(modelName, viewId || 0);
            if (!config || !config.columns) return;

            const hiddenSet = new Set(
                config.columns.filter(c => c.hidden).map(c => c.name)
            );

            const table = this.el?.querySelector("table");
            if (!table) return;

            const thead = table.querySelector("thead tr:first-child");
            if (!thead) return;

            // Hide / show TH header cells
            thead.querySelectorAll("th[data-name]").forEach((th) => {
                th.style.display = hiddenSet.has(th.dataset.name) ? "none" : "";
            });

            // Hide / show TD data cells
            table.querySelectorAll("tbody tr").forEach((row) => {
                row.querySelectorAll("td[data-name]").forEach((td) => {
                    td.style.display = hiddenSet.has(td.dataset.name) ? "none" : "";
                });
            });

            // Hide / show tfoot cells (totals row)
            const tfoot = table.querySelector("tfoot");
            if (tfoot) {
                tfoot.querySelectorAll("td[data-name], th[data-name]").forEach((cell) => {
                    cell.style.display = hiddenSet.has(cell.dataset.name) ? "none" : "";
                });
            }
        } catch (e) {
            console.warn("[Inom LVM] _inomApplyHiddenColumns error:", e);
        }
    },

    // ─────────────────────────────────────────────────────────────────────────
    // FIX 2 — Rename Columns
    // Reads config directly from DB (not cache) to avoid timing issues
    // ─────────────────────────────────────────────────────────────────────────
    async _inomApplyColumnLabels() {
        try {
            const modelName = this.props.list?.resModel;
            const viewId    = this.props.archInfo?.viewId;
            if (!modelName) return;

            const config = await this.inomService.loadConfig(modelName, viewId || 0);
            if (!config || !config.columns) return;

            const labelsMap = {};
            config.columns.forEach(c => {
                if (c.label) labelsMap[c.name] = c.label;
            });
            if (!Object.keys(labelsMap).length) return;

            const table = this.el?.querySelector("table");
            if (!table) return;

            const thead = table.querySelector("thead tr:first-child");
            if (!thead) return;

            thead.querySelectorAll("th[data-name]").forEach((th) => {
                const newLabel = labelsMap[th.dataset.name];
                if (!newLabel) return;

                // Strategy 1: find meaningful <span> (not resize/sort/icon spans)
                const span = Array.from(th.querySelectorAll("span")).find((s) => {
                    const cls = s.className || "";
                    return (
                        !cls.includes("o_resize") &&
                        !cls.includes("fa") &&
                        !cls.includes("o_sort") &&
                        s.textContent.trim().length > 0
                    );
                });
                if (span) {
                    span.textContent = newLabel;
                    return;
                }

                // Strategy 2: update first non-empty text node
                for (const node of th.childNodes) {
                    if (node.nodeType === Node.TEXT_NODE && node.textContent.trim()) {
                        node.textContent = " " + newLabel + " ";
                        return;
                    }
                }

                // Strategy 3: inject a label span safely
                let labelSpan = th.querySelector(".inom-lvm-label");
                if (!labelSpan) {
                    labelSpan = document.createElement("span");
                    labelSpan.className = "inom-lvm-label";
                    const resizeHandle = th.querySelector(".o_resize, .inom-resize-handle");
                    if (resizeHandle) {
                        th.insertBefore(labelSpan, resizeHandle);
                    } else {
                        th.prepend(labelSpan);
                    }
                }
                labelSpan.textContent = newLabel;
            });
        } catch (e) {
            console.warn("[Inom LVM] _inomApplyColumnLabels error:", e);
        }
    },

    // ─────────────────────────────────────────────────────────────────────────
    // EXISTING — Reorder columns in DOM (unchanged)
    // ─────────────────────────────────────────────────────────────────────────
    _inomApplyColumnOrderToDOM() {
        try {
            const modelName = this.props.list?.resModel;
            const viewId    = this.props.archInfo?.viewId;
            if (!modelName) return;

            const orderMap = this.inomService.getColumnOrder(modelName, viewId);
            if (!orderMap || !Object.keys(orderMap).length) return;

            const table = this.el?.querySelector("table");
            if (!table) return;

            const thead = table.querySelector("thead tr:first-child");
            if (!thead) return;

            const ths = Array.from(thead.querySelectorAll("th[data-name]"));
            if (!ths.length) return;

            const sortedThs = [...ths].sort((a, b) =>
                (orderMap[a.dataset.name] ?? 9999) - (orderMap[b.dataset.name] ?? 9999)
            );

            const currentOrder = ths.map(th => th.dataset.name);
            const desiredOrder = sortedThs.map(th => th.dataset.name);
            if (JSON.stringify(currentOrder) === JSON.stringify(desiredOrder)) return;

            sortedThs.forEach(th => thead.appendChild(th));

            table.querySelectorAll("tbody tr").forEach(row => {
                const tds = Array.from(row.querySelectorAll("td[data-name]"));
                if (!tds.length) return;
                [...tds]
                    .sort((a, b) =>
                        (orderMap[a.dataset.name] ?? 9999) - (orderMap[b.dataset.name] ?? 9999)
                    )
                    .forEach(td => row.appendChild(td));
            });
        } catch (e) {
            console.warn("[Inom LVM] _inomApplyColumnOrderToDOM error:", e);
        }
    },

    // ─────────────────────────────────────────────────────────────────────────
    // EXISTING — Apply saved column widths (unchanged)
    // ─────────────────────────────────────────────────────────────────────────
    async _applySavedColumnWidths() {
        try {
            const modelName = this.props.list?.resModel;
            const viewId    = this.props.archInfo?.viewId;
            if (!modelName || !viewId) return;

            const config = await this.inomService.loadConfig(modelName, viewId);
            if (!config || !config.columns) return;

            const table = this.el?.querySelector("table");
            if (!table) return;

            table.querySelectorAll("thead th[data-name]").forEach((th) => {
                const column = config.columns.find(c => c.name === th.dataset.name);
                if (column && column.width) {
                    th.style.width    = column.width + "px";
                    th.style.minWidth = column.width + "px";
                    th.style.maxWidth = column.width + "px";
                    table.querySelectorAll("tbody tr").forEach((tr) => {
                        const td = tr.querySelector(`td[data-name="${th.dataset.name}"]`);
                        if (td) {
                            td.style.width    = column.width + "px";
                            td.style.minWidth = column.width + "px";
                            td.style.maxWidth = column.width + "px";
                        }
                    });
                }
            });
        } catch (error) {
            console.warn("[Inom LVM] Column width apply failed:", error);
        }
    },

    // ─────────────────────────────────────────────────────────────────────────
    // EXISTING — Drag-to-resize handles (unchanged)
    // ─────────────────────────────────────────────────────────────────────────
    _enableColumnResize() {
        if (!this.el) return;

        const table = (this.tableRef && this.tableRef.el)
            ? this.tableRef.el
            : this.el.querySelector("table");

        if (!table || table.dataset.resizeInit) return;
        table.dataset.resizeInit = true;

        table.querySelectorAll("thead th[data-name]").forEach((th) => {
            if (th.querySelector(".inom-resize-handle")) return;

            th.style.position = "relative";

            const handle = document.createElement("div");
            handle.className = "inom-resize-handle";
            Object.assign(handle.style, {
                position: "absolute",
                top: 0, right: 0,
                width: "6px", height: "100%",
                cursor: "col-resize", zIndex: "100",
            });
            th.appendChild(handle);

            let startX = 0, startWidth = 0;
            const fieldName = th.dataset.name;

            const mouseMove = (ev) => {
                const width = startWidth + (ev.pageX - startX);
                th.style.width = th.style.minWidth = width + "px";
                table.querySelectorAll("tbody tr").forEach((tr) => {
                    const td = tr.querySelector(`td[data-name="${fieldName}"]`);
                    if (td) td.style.width = td.style.minWidth = width + "px";
                });
            };

            const mouseUp = async () => {
                document.removeEventListener("mousemove", mouseMove);
                document.removeEventListener("mouseup", mouseUp);
                try {
                    const modelName = this.props.list?.resModel;
                    const viewId    = this.props.archInfo?.viewId;
                    const config    = await this.inomService.loadConfig(modelName, viewId);
                    if (!config.columns) config.columns = [];
                    let column = config.columns.find(c => c.name === fieldName);
                    if (!column) { column = { name: fieldName }; config.columns.push(column); }
                    column.width = parseInt(th.offsetWidth);
                    await this.inomService.saveConfig(modelName, viewId, config);
                } catch (err) {
                    console.warn("[Inom LVM] Width save failed:", err);
                }
            };

            handle.addEventListener("mousedown", (ev) => {
                ev.preventDefault();
                startX = ev.pageX;
                startWidth = th.offsetWidth;
                document.addEventListener("mousemove", mouseMove);
                document.addEventListener("mouseup", mouseUp);
            });
        });
    },
});