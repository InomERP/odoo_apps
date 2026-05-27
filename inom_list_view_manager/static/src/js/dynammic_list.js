/** @odoo-module **/

import { Component, useState, useRef, onMounted, onWillUpdateProps } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";

export class InomDynamicListPanel extends Component {
    static template = "inom_list_view_manager.DynamicListPanel";

    static props = {
        columns: Array,
        modelName: String,
        viewId: Number,
        onConfigChange: Function,
        onAutoSave: Function,
    };

    setup() {
        this.inomService = useService("inom_list_view_manager");
        this.columnListRef = useRef("columnList");
        this.btnRef = useRef("toggleBtn");

        this.state = useState({
            panelOpen: false,
            searchTerm: "",
            renamingColumn: null,
            dropTop: 0,
            dropRight: 0,
            columns: this.props.columns.map(c => ({ ...c })),
        });

        this._dragSrcName = null;
        this._dragOverName = null;
        this._isAutoSaving = false;

        onWillUpdateProps((nextProps) => {
            if (!this.state.panelOpen || this._isAutoSaving) return;
            this.state.columns = nextProps.columns.map(c => ({ ...c }));
        });

        onMounted(async () => {
            const toggleColor     = await this.inomService.getToggleColor();
            const headerColor     = await this.inomService.getHeaderColor();
            const headerTextColor = await this.inomService.getHeaderTextColor();
            document.documentElement.style.setProperty('--lvm-toggle-color', toggleColor);
            document.documentElement.style.setProperty('--lvm-header-color', headerColor);
            document.documentElement.style.setProperty('--lvm-header-text-color', headerTextColor);
        });
    }

    get filteredColumns() {
        const term = (this.state.searchTerm || "").toLowerCase();
        return [...this.state.columns]
            .filter(c => c.label.toLowerCase().includes(term))
            .sort((a, b) => a.order - b.order);
    }

    togglePanel() {
        if (!this.state.panelOpen) {
            const btn = this.btnRef.el;
            if (btn) {
                const rect = btn.getBoundingClientRect();
                this.state.dropRight = window.innerWidth - rect.right - 25;
            }
            this.state.panelOpen = true;
        } else {
            this.state.panelOpen = false;
        }
    }

    closePanel() {
        this.state.panelOpen = false;
    }

    async _autoSave() {
        try {
            this._isAutoSaving = true;

            const sortedColumns = [...this.state.columns].sort((a, b) => a.order - b.order);
            sortedColumns.forEach((col, idx) => { col.order = idx; });

            const config = { columns: sortedColumns };
            await this.inomService.saveConfig(this.props.modelName, this.props.viewId, config);

            const orderMap = {};
            sortedColumns.forEach(c => { orderMap[c.name] = c.order; });
            this.inomService.setColumnOrder(this.props.modelName, this.props.viewId, orderMap);

            await this.props.onAutoSave(config);

            console.log('[Inom LVM] Auto-saved config');
        } catch (e) {
            console.error('[Inom LVM] Auto-save failed:', e);
        } finally {
            this._isAutoSaving = false;
        }
    }

    toggleColumn(name, isVisible) {
        const col = this.state.columns.find(c => c.name === name);
        if (col) col.hidden = !isVisible;
        this._autoSave();
    }

    startRename(name) {
        this.state.renamingColumn = name;
        setTimeout(() => {
            const row = document.querySelector(`.inom-lvm-row[data-name="${name}"]`);
            if (row) {
                const input = row.querySelector('input[type="text"]');
                if (input) {
                    input.focus();
                    input.setSelectionRange(input.value.length, input.value.length);
                }
            }
        }, 50);
    }

    finishRename(name, newLabel) {
        const col = this.state.columns.find(c => c.name === name);
        const trimmed = (newLabel || '').trim();
        if (col && trimmed) col.label = trimmed;
        this.state.renamingColumn = null;
        if (col && trimmed) this._autoSave();
    }

    onRenameKey(name, ev) {
        if (ev.key === 'Enter') {
            ev.preventDefault();
            this.finishRename(name, ev.target.value);
        } else if (ev.key === 'Escape') {
            this.state.renamingColumn = null;
        }
    }

    onLabelDblClick(name) {
        this.startRename(name);
    }

    onSearchInput(ev) {
        this.state.searchTerm = ev.target.value;
    }

    onDragStart(ev, name) {
        this._dragSrcName = name;
        ev.dataTransfer.effectAllowed = "move";
        ev.dataTransfer.setData("text/plain", name);
        ev.currentTarget.classList.add("inom-dragging");
    }

    // FIX: name parameter added to match XML binding (ev) => this.onDragOver(ev, col.name)
    onDragOver(ev, name) {
        ev.preventDefault();
        ev.dataTransfer.dropEffect = "move";
        this._dragOverName = name;

        const list = this.columnListRef.el;
        if (list) {
            list.querySelectorAll(".inom-lvm-row").forEach(r => {
                r.classList.remove("inom-drag-over-top", "inom-drag-over-bottom");
            });
            const target = list.querySelector(`.inom-lvm-row[data-name="${name}"]`);
            if (target && name !== this._dragSrcName) {
                const rect = target.getBoundingClientRect();
                const isAbove = ev.clientY < rect.top + rect.height / 2;
                target.classList.add(isAbove ? "inom-drag-over-top" : "inom-drag-over-bottom");
            }
        }
    }

    // FIX: Missing handler — referenced in XML but never defined, causing drag to silently fail
    onDragEnter(ev, name) {
        ev.preventDefault();
    }

    onDragEnd(ev) {
        const list = this.columnListRef.el;
        if (list) {
            list.querySelectorAll(".inom-lvm-row").forEach(r => {
                r.classList.remove("inom-dragging", "inom-drag-over-top", "inom-drag-over-bottom");
            });
        }
        this._dragSrcName = null;
        this._dragOverName = null;
    }

    onDrop(ev, targetName) {
        ev.preventDefault();
        const srcName = this._dragSrcName || ev.dataTransfer.getData("text/plain");

        if (!srcName || srcName === targetName) return;

        const src = this.state.columns.find(c => c.name === srcName);
        const tgt = this.state.columns.find(c => c.name === targetName);
        if (!src || !tgt) return;

        const targetEl = ev.currentTarget;
        const rect = targetEl.getBoundingClientRect();
        const insertBefore = ev.clientY < rect.top + rect.height / 2;

        const sorted = [...this.state.columns].sort((a, b) => a.order - b.order);

        const srcIdx = sorted.findIndex(c => c.name === srcName);
        const [removed] = sorted.splice(srcIdx, 1);

        let tgtIdx = sorted.findIndex(c => c.name === targetName);
        if (!insertBefore) tgtIdx += 1;

        sorted.splice(tgtIdx, 0, removed);
        sorted.forEach((col, idx) => { col.order = idx; });

        this.state.columns = [...this.state.columns];
        console.log("[Inom LVM] Drop — new order:", sorted.map(c => c.name));

        this._autoSave();
    }

    async applyAndClose() {
        const sortedColumns = [...this.state.columns].sort((a, b) => a.order - b.order);
        sortedColumns.forEach((col, idx) => { col.order = idx; });
        this.state.columns = sortedColumns;

        const config = { columns: this.state.columns };
        await this.inomService.saveConfig(this.props.modelName, this.props.viewId, config);

        const orderMap = {};
        sortedColumns.forEach(c => { orderMap[c.name] = c.order; });
        this.inomService.setColumnOrder(this.props.modelName, this.props.viewId, orderMap);

        this.props.onConfigChange(config);
        this.closePanel();
    }

    async resetToDefault() {
        await this.inomService.resetConfig(this.props.modelName, this.props.viewId);
        this.inomService.setColumnOrder(this.props.modelName, this.props.viewId, {});
        this.props.onConfigChange(null);
        this.closePanel();
    }
}

registry.category("components").add("InomDynamicListPanel", InomDynamicListPanel);