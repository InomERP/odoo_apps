/** @odoo-module **/

import { ListController } from "@web/views/list/list_controller";
import { patch } from "@web/core/utils/patch";
import { useState, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

patch(ListController.prototype, {
    setup() {
        super.setup(...arguments);
        this.inomService = useService("inom_list_view_manager");
        this.inomState = useState({ savedConfig: null });

        onWillStart(async () => {
            try {
                const config = await this.inomService.loadConfig(
                    this.props.resModel,
                    this.props.info?.viewId || 0
                );
                this.inomState.savedConfig = config;
                this._inomSyncConfig(config);
            } catch (e) {
                console.warn("[Inom LVM] setup error:", e);
            }
        });

        // NOTE: The old onPatched() here used to re-shuffle <th>/<td> nodes in
        // the DOM with appendChild. In Odoo 19 OWL re-renders the table from
        // `this.columns`, so that manual DOM reorder was reverted on the very
        // next patch (this was the real reason "drag & drop reorder" never
        // stuck). Reordering is now done at the data layer inside the
        // ListRenderer patch (onWillRender), so nothing is needed here.
    },

    // ROOT CAUSE of "this.inomService.setViewId is not a function":
    //   setViewId/getViewId were NEW service methods. If the JS asset bundle is
    //   even partially cached/stale (very common after an upgrade), the running
    //   service instance can be the OLD class WITHOUT those methods, while the
    //   controller is the NEW one that calls them. Because setViewId was the
    //   FIRST line of _inomSyncConfig, it threw immediately and aborted the
    //   whole sync — so hide/show, reorder, rename AND restore all silently
    //   stopped working at once (their caches were never set).
    //
    //   FIX: never depend on that service METHOD. Stash the view id directly on
    //   the service instance's plain dict (creating it if needed). This works
    //   with the old OR the new service class and can never be "not a function".
    _inomStashViewId(modelName, viewId) {
        const svc = this.inomService;
        if (!svc) return;
        if (typeof svc.setViewId === "function") {
            svc.setViewId(modelName, viewId);
            return;
        }
        svc._viewIdByModel = svc._viewIdByModel || {};
        svc._viewIdByModel[modelName] = viewId || 0;
    },

    _inomSyncConfig(config) {
        try {
            const modelName = this.props.resModel;
            const viewId    = this.props.info?.viewId || 0;

            // Publish the canonical view id so the renderer (widths) and the
            // panel all read/write the SAME DB row. (Crash-proof, see above.)
            this._inomStashViewId(modelName, viewId);

            const hiddenNames = (config?.columns || [])
                .filter(c => c.hidden)
                .map(c => c.name);
            this.inomService.setHiddenColumns(modelName, viewId, hiddenNames);

            const labelsMap = {};
            (config?.columns || []).forEach(c => {
                if (c.label) labelsMap[c.name] = c.label;
            });
            this.inomService.setColumnLabels(modelName, viewId, labelsMap);

            const orderMap = {};
            (config?.columns || []).forEach(c => {
                if (c.order !== undefined && c.order !== null) {
                    orderMap[c.name] = c.order;
                }
            });
            this.inomService.setColumnOrder(modelName, viewId, orderMap);
        } catch (e) {
            // Never let a sync error abort the save / apply flow.
            console.warn("[Inom LVM] _inomSyncConfig error:", e);
        }
    },

    get inomDynamicColumns() {
        try {
            const archCols = this.props?.archInfo?.columns || [];
            let cols = archCols.filter(c => c.type === "field" && c.name);

            if (!cols.length && this.props?.fields) {
                cols = Object.entries(this.props.fields).map(([name, f]) => ({
                    type: "field", name, string: f.string || name,
                }));
            }

            const config    = this.inomState?.savedConfig || {};
            const configMap = {};
            (config.columns || []).forEach(c => { configMap[c.name] = c; });

            return cols.map((col, idx) => ({
                name:   col.name,
                label:  configMap[col.name]?.label  || col.string || col.name,
                hidden: configMap[col.name]?.hidden ?? false,
                order:  configMap[col.name]?.order  ?? idx,
            }));
        } catch (e) {
            console.warn("[Inom LVM] inomDynamicColumns error:", e);
            return [];
        }
    },

    // Rename / reorder / hide are VIEW-ONLY changes — they do not need a data
    // reload. `this.model.load()` depended on the model's reactivity actually
    // re-rendering the renderer, which was unreliable. A forced deep re-render
    // (`this.render(true)`) is guaranteed to re-run the ListRenderer's
    // onWillRender (reorder + rename) and onPatched (hide/show) so the changes
    // ALWAYS reflect instantly. We keep a model.load() fallback just in case a
    // future Odoo build removes Component.render.
    _inomForceRerender() {
        try {
            if (typeof this.render === "function") {
                this.render(true);
                return;
            }
        } catch (e) {
            console.warn("[Inom LVM] render(true) failed, falling back:", e);
        }
        // Fallback: reload the data which also re-renders.
        if (this.model && typeof this.model.load === "function") {
            this.model.load();
        }
    },

    async inomOnConfigChange(newConfig) {
        this.inomState.savedConfig = newConfig;
        this._inomSyncConfig(newConfig);
        this._inomForceRerender();
    },

    async inomOnAutoSave(newConfig) {
        this.inomState.savedConfig = newConfig;
        this._inomSyncConfig(newConfig);
        this._inomForceRerender();
    },
});