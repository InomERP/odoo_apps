/** @odoo-module **/

import { registry } from "@web/core/registry";

class InomListViewManagerService {
    constructor(env, services) {
        this.orm = services.orm;
        this._hiddenColumnsCache = {};
        this._columnLabelsCache  = {};
        this._columnOrderCache   = {};
    }

    // ============================================================
    // HIDDEN COLUMNS CACHE
    // ============================================================
    setHiddenColumns(modelName, viewId, hiddenNames) {
        // KEY FIX: viewId hata diya — sirf modelName use karo
        this._hiddenColumnsCache[modelName] = new Set(hiddenNames || []);
    }

    getHiddenColumns(modelName, viewId) {
        return this._hiddenColumnsCache[modelName] || new Set();
    }

    // ============================================================
    // COLUMN LABELS CACHE
    // ============================================================
    setColumnLabels(modelName, viewId, labelsMap) {
        // KEY FIX: viewId hata diya
        this._columnLabelsCache[modelName] = labelsMap || {};
    }

    getColumnLabels(modelName, viewId) {
        return this._columnLabelsCache[modelName] || {};
    }

    // ============================================================
    // COLUMN ORDER CACHE
    // ============================================================
    setColumnOrder(modelName, viewId, orderMap) {
        // KEY FIX: viewId hata diya
        this._columnOrderCache[modelName] = orderMap || {};
        console.log('[Inom LVM] setColumnOrder key=', modelName, orderMap);
    }

    getColumnOrder(modelName, viewId) {
        console.log('[Inom LVM] getColumnOrder key=', modelName, this._columnOrderCache[modelName]);
        return this._columnOrderCache[modelName] || {};
    }

    // ============================================================
    // RPC: Load / Save / Reset  (DB mein viewId sahi rehta hai)
    // ============================================================
    async loadConfig(modelName, viewId) {
        try {
            const jsonStr = await this.orm.call(
                'inom.list.view.manager',
                'inom_get_column_config',
                [modelName, viewId]
            );
            return JSON.parse(jsonStr || '{}');
        } catch (e) {
            console.warn('[Inom LVM] Could not load config:', e);
            return {};
        }
    }

    async saveConfig(modelName, viewId, config) {
        try {
            await this.orm.call(
                'inom.list.view.manager',
                'inom_save_column_config',
                [modelName, viewId, JSON.stringify(config)]
            );
        } catch (e) {
            console.error('[Inom LVM] Could not save config:', e);
        }
    }

    async resetConfig(modelName, viewId) {
        try {
            await this.orm.call(
                'inom.list.view.manager',
                'inom_reset_column_config',
                [modelName, viewId]
            );
        } catch (e) {
            console.error('[Inom LVM] Could not reset config:', e);
        }
    }

    // ============================================================
    // COLORS
    // ============================================================
    async getToggleColor() {
        return await this.orm.call("inom.list.view.manager", "get_toggle_color", []);
    }

    async getHeaderColor() {
        return await this.orm.call("inom.list.view.manager", "get_header_color", []);
    }

    async getHeaderTextColor() {
        return await this.orm.call("inom.list.view.manager", "get_header_text_color", []);
    }
}

registry.category("services").add("inom_list_view_manager", {
    dependencies: ["orm"],
    start(env, services) {
        return new InomListViewManagerService(env, services);
    },
});

document.documentElement.style.setProperty('--lvm-toggle-color', '#875A7B');
document.documentElement.style.setProperty('--lvm-header-color', '#875A7B');
document.documentElement.style.setProperty('--lvm-header-text-color', '#ffffff');