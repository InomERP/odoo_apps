/** @odoo-module **/

/**
 * SINGLE source of truth for the ListRenderer column features
 * (reorder, rename, hide/show, width restore, drag-to-resize).
 *
 * Why the rewrite:
 *  - Reorder & rename used to be done by mutating the rendered DOM
 *    (appendChild / textContent) inside onPatched. In Odoo 19 the header
 *    (`t-foreach="columns"`) and the data cells (`getColumns()` -> `this.columns`)
 *    are rendered by OWL from `this.columns`. Any manual DOM shuffle / text
 *    rewrite is therefore reverted on the very next render. That is the real
 *    reason "drag & drop reorder" and "rename" never reflected in the list.
 *
 *  - The fix applies order + labels at the DATA layer (`this.columns` /
 *    `this.allColumns`) inside `onWillRender`, so OWL renders them natively
 *    and they PERSIST across every re-render — no flicker, no revert.
 *
 *  - Hide/show keeps the existing (working) `display:none` DOM approach, but
 *    now reads from the per-model cache instead of doing an RPC on every patch
 *    with the wrong view id.
 *
 *  - The duplicate ListRenderer patch that previously lived in
 *    list_column_resize.js is removed there (that file is now inert) so this
 *    logic only runs once.
 */

import { ListRenderer } from "@web/views/list/list_renderer";
import { patch } from "@web/core/utils/patch";
import { onMounted, onPatched, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

patch(ListRenderer.prototype, {
    setup() {
        super.setup(...arguments);

        this.inomService = useService("inom_list_view_manager");

        // ROOT CAUSE of "saved settings not restoring": the renderer used to
        // depend on the ListController having already populated the per-model
        // caches before the renderer's first render. If the controller patch
        // and renderer patch resolve in a different order (or key the cache by
        // a slightly different model name), the very first paint had no config
        // and nothing restored.
        //
        // FIX: the renderer now loads its OWN config in onWillStart (which OWL
        // awaits before the first render) and populates the caches under the
        // exact model name it will read back. This makes restore-after-refresh
        // bulletproof and independent of the controller's timing.
        onWillStart(async () => {
            try {
                const modelName = this.props.list?.resModel;
                if (!modelName) return;
                const viewId = this._inomGetViewId(modelName);
                const config = await this.inomService.loadConfig(modelName, viewId);
                this._inomPopulateCaches(modelName, viewId, config);
            } catch (e) {
                console.warn("[Inom LVM] renderer onWillStart load error:", e);
            }
        });

        // REORDER + HIDE + RENAME are applied by overriding getActiveColumns()
        // below — NOT via onWillRender. Reason: OWL runs onWillRender callbacks
        // in REVERSE registration order, so the CORE renderer's own onWillRender
        // (which does `this.columns = this.getActiveColumns()`) runs AFTER ours
        // and wipes any change we make there. Overriding getActiveColumns() means
        // the core's own reset produces our transformed columns, so it sticks
        // through every render.

        // DOM-layer (AFTER render): width restore + resize handles only.
        onMounted(async () => {
            await this._applySavedColumnWidths();
            this._enableColumnResize();
        });

        onPatched(async () => {
            await this._applySavedColumnWidths();
            this._enableColumnResize();
        });
    },

    // ─────────────────────────────────────────────────────────────────────────
    // THE hook that actually works: the core ListRenderer builds this.columns
    // (header + rows + footer all read it) from getActiveColumns() on EVERY
    // render. By transforming its result we apply rename + hide + reorder in a
    // way that survives the core's per-render rebuild.
    // ─────────────────────────────────────────────────────────────────────────
    getActiveColumns() {
        const cols = super.getActiveColumns(...arguments);
        return this._inomTransformColumns(cols);
    },

    _inomTransformColumns(cols) {
        try {
            const modelName = this.props.list?.resModel;
            if (!modelName || !Array.isArray(cols)) return cols;

            const labelsMap = this.inomService.getColumnLabels(modelName) || {};
            const orderMap  = this.inomService.getColumnOrder(modelName)  || {};
            const hiddenSet = this.inomService.getHiddenColumns(modelName) || new Set();

            // Snapshot the original arch order ONCE (names are stable even though
            // the column OBJECTS are recreated each render) so Reset can restore.
            if (!this._inomDefaultOrder) {
                this._inomDefaultOrder = {};
                cols.forEach((c, i) => {
                    if (c && c.name) this._inomDefaultOrder[c.name] = i;
                });
            }

            // ── RENAME ── set column.label; remember original for Reset.
            cols.forEach((col) => {
                if (!col || !col.name) return;
                if (col._inomOriginalLabel === undefined) {
                    col._inomOriginalLabel = col.label;
                }
                col.label = labelsMap[col.name] || col._inomOriginalLabel;
            });

            // ── HIDE / SHOW ── drop hidden columns (removes header + rows + footer).
            let visible = cols.filter(
                (c) => !(c && c.name && hiddenSet.has(c.name))
            );

            // ── REORDER ── stable sort by saved order (or default order on Reset).
            const map = Object.keys(orderMap).length
                ? orderMap
                : this._inomDefaultOrder;
            if (map && Object.keys(map).length) {
                const rank = (c) => (c && c.name in map ? map[c.name] : 9999);
                visible = [...visible].sort((a, b) => rank(a) - rank(b));
            }

            return visible;
        } catch (e) {
            console.warn("[Inom LVM] _inomTransformColumns error:", e);
            return cols;
        }
    },

    // Crash-proof view-id read (mirrors the controller's _inomStashViewId).
    // Never depends on the service's getViewId METHOD, which may be absent on a
    // stale/partial asset bundle.
    _inomGetViewId(modelName) {
        const svc = this.inomService;
        if (!svc) return 0;
        if (typeof svc.getViewId === "function") {
            return svc.getViewId(modelName);
        }
        return (svc._viewIdByModel && svc._viewIdByModel[modelName]) || 0;
    },

    // ─────────────────────────────────────────────────────────────────────────
    // Populate the per-model caches from a loaded config (used on first paint
    // so the renderer is self-sufficient even before the controller syncs).
    // ─────────────────────────────────────────────────────────────────────────
    _inomPopulateCaches(modelName, viewId, config) {
        const columns = (config && config.columns) || [];

        const hiddenNames = columns.filter(c => c.hidden).map(c => c.name);
        this.inomService.setHiddenColumns(modelName, viewId, hiddenNames);

        const labelsMap = {};
        columns.forEach(c => { if (c.label) labelsMap[c.name] = c.label; });
        this.inomService.setColumnLabels(modelName, viewId, labelsMap);

        const orderMap = {};
        columns.forEach(c => {
            if (c.order !== undefined && c.order !== null) {
                orderMap[c.name] = c.order;
            }
        });
        this.inomService.setColumnOrder(modelName, viewId, orderMap);
    },

    // ─────────────────────────────────────────────────────────────────────────
    // WIDTH RESTORE — uses the canonical view id (same DB row as the config)
    // ─────────────────────────────────────────────────────────────────────────
    async _applySavedColumnWidths() {
        try {
            const modelName = this.props.list?.resModel;
            if (!modelName) return;

            const viewId = this._inomGetViewId(modelName);
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
    // DRAG-TO-RESIZE HANDLES — uses the canonical view id when saving
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
                    const viewId    = this._inomGetViewId(modelName);
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