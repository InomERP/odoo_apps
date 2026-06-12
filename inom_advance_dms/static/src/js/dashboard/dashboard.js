/** @odoo-module **/
/**
 * Advanced DMS - Document Dashboard (folder browser edition)
 *
 * Premium OWL client action: navigate into folders, see the files/folders
 * inside, drag & drop to upload, and act on each document through a kebab
 * menu (Open / Download / Share access / Request approval / Annotate PDF).
 *
 * Reads data through the additive `/edm/dashboard/data` and
 * `/edm/dashboard/folder` controllers and reuses existing wizards/actions,
 * so no existing business logic is touched.
 */

import { Component, useState, onWillStart, onWillUnmount, useExternalListener } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { jsonrpc } from "@web/core/network/rpc_service";
import { session } from "@web/session";
import { openAnnotator } from "../pdf_annotator";

const FOLDER_PALETTE = [
    "#6366f1", "#10b981", "#f59e0b", "#f43f5e", "#06b6d4",
    "#8b5cf6", "#14b8a6", "#ec4899", "#3b82f6", "#f97316",
];

const EXT_COLORS = {
    pdf: "#f43f5e",
    doc: "#3b82f6", docx: "#3b82f6",
    xls: "#10b981", xlsx: "#10b981",
    png: "#8b5cf6", jpg: "#8b5cf6", jpeg: "#8b5cf6",
    txt: "#64748b", csv: "#14b8a6",
    ppt: "#ea580c", pptx: "#ea580c",
    gif: "#8b5cf6", svg: "#8b5cf6", webp: "#8b5cf6",
    zip: "#f59e0b",
    url: "#06b6d4",
};

const EXT_ICONS = {
    pdf: "fa-file-pdf-o",
    doc: "fa-file-word-o", docx: "fa-file-word-o",
    xls: "fa-file-excel-o", xlsx: "fa-file-excel-o",
    png: "fa-file-image-o", jpg: "fa-file-image-o", jpeg: "fa-file-image-o",
    txt: "fa-file-text-o", csv: "fa-file-text-o",
    ppt: "fa-file-powerpoint-o", pptx: "fa-file-powerpoint-o",
    gif: "fa-file-image-o", svg: "fa-file-image-o", webp: "fa-file-image-o",
    zip: "fa-file-archive-o",
    url: "fa-link",
};

const PAGE_SIZE = 12;

export class EdmDashboard extends Component {
    static template = "inom_advance_dms.Dashboard";
    static props = ["*"];

    setup() {
        this.action = useService("action");
        this.notification = useService("notification");
        this.orm = useService("orm");

        this.state = useState({
            loading: true,
            error: false,
            uploading: false,
            dragActive: false,
            search: "",
            sideSearch: "",
            activeTab: "all",
            page: 1,
            menu: { open: false, x: 0, y: 0, id: false, isPdf: false },
            currentFolderId: false,
            breadcrumb: [],
            subfolders: [],
            documents: [],
            sharedDocs: [],   // documents shared with me (inline Shared tab)
            sharedPopup: { open: false },
            folders: [],       // top-level folders for the sidebar
            popup: { open: false, id: null, name: "", ext: "", isPdf: false, preview: false },
            stats: {},
            storage: {},
            charts: {},
            latest: [],
        });

        // Clicking anywhere (or scrolling) closes any open kebab menu.
        useExternalListener(window, "click", () => {
            this.state.menu.open = false;
        });
        useExternalListener(window, "scroll", () => {
            this.state.menu.open = false;
        }, { capture: true });

        onWillStart(async () => {
            await this.loadSummary();
            await this.loadFolder(false);
        });

        onWillUnmount(() => {});
    }

    // ------------------------------------------------------------------
    // Data
    // ------------------------------------------------------------------
    async loadSummary() {
        try {
            const result = await jsonrpc("/edm/dashboard/data", {
                date_from: null,
                date_to: null,
            });
            if (result && result.status === "ok") {
                this.state.stats = result.stats || {};
                this.state.folders = result.folders || [];
                this.state.storage = result.storage || {};
                this.state.charts = result.charts || {};
                this.state.latest = (result.latest_documents || []).map(d => Object.assign({}, d, { create_date: (d.create_date || "").slice(0, 10) }));
            } else {
                this.state.error = true;
            }
        } catch {
            this.state.error = true;
        }
    }

    get trendChart() {
        const t = (this.state.charts && this.state.charts.upload_trend) || { labels: [], data: [] };
        const data = t.data || [];
        const labels = t.labels || [];
        const n = data.length;
        const W = 100, H = 40;
        const max = Math.max(1, ...data);
        const pts = data.map((v, i) => {
            const x = n <= 1 ? 0 : (i / (n - 1)) * W;
            const y = H - (v / max) * (H - 6) - 3;
            return { x: Number(x.toFixed(2)), y: Number(y.toFixed(2)), v: v, label: labels[i] || "" };
        });
        let line = "";
        pts.forEach((p, i) => { line += (i === 0 ? "M" : "L") + p.x + " " + p.y + " "; });
        let area = "";
        if (pts.length) {
            area = "M" + pts[0].x + " " + H + " ";
            pts.forEach((p) => { area += "L" + p.x + " " + p.y + " "; });
            area += "L" + pts[pts.length - 1].x + " " + H + " Z";
        }
        return { line: line.trim(), area: area.trim(), points: pts, total: data.reduce((a, b) => a + b, 0) };
    }

    get trendBars() {
        const c = (this.state.charts && this.state.charts.upload_trend) || { labels: [], data: [] };
        const data = c.data || [];
        const max = Math.max(1, ...data);
        return data.map((v, i) => ({ h: Math.round((v / max) * 100), value: v, label: (c.labels && c.labels[i]) || "" }));
    }

    get statusRows() {
        const c = (this.state.charts && this.state.charts.status) || { labels: [], data: [] };
        const data = c.data || [];
        const labels = c.labels || [];
        const colors = ["#9aa1b2", "#f59e0b", "#22c55e", "#ef4444", "#6366f1", "#06b6d4"];
        const max = Math.max(1, ...data);
        const total = data.reduce((a, b) => a + b, 0) || 1;
        return data.map((v, i) => ({ label: labels[i] || "", value: v, w: Math.round((v / max) * 100), pct: Math.round((v / total) * 100), color: colors[i % colors.length] }));
    }

    async loadFolder(folderId) {
        this.state.loading = true;
        this.state.error = false;
        this.state.menu.open = false;
        try {
            const result = await jsonrpc("/edm/dashboard/folder", {
                folder_id: folderId || null,
            });
            if (result && result.status === "ok") {
                this.state.currentFolderId = result.folder_id || false;
                this.state.subfolders = result.subfolders || [];
                this.state.documents = result.documents || [];
                this.state.breadcrumb = result.breadcrumb || [];
                this.state.page = 1;
            } else {
                this.state.error = true;
            }
        } catch {
            this.state.error = true;
        } finally {
            this.state.loading = false;
        }
    }

    async loadShared() {
        this.state.menu.open = false;
        try {
            const uid = session.uid;
            const recs = await this.orm.searchRead(
                "edm.document",
                [["is_trashed", "=", false], ["allowed_user_ids", "in", [uid]], ["owner_id", "!=", uid]],
                ["name", "file_extension", "state", "owner_id"],
                { order: "create_date desc" }
            );
            this.state.sharedDocs = (recs || []).map((d) => {
                const ext = (d.file_extension || "").toLowerCase();
                return {
                    id: d.id,
                    name: d.name,
                    extension: ext || "file",
                    is_pdf: ext === "pdf",
                    state: d.state || "draft",
                    owner: d.owner_id ? d.owner_id[1] : "",
                };
            });
        } catch {
            this.state.sharedDocs = [];
            this.notification.add("Unable to load shared documents.", { type: "danger" });
        }
    }

    async openSharedPopup() {
        await this.loadShared();
        const docs = this.state.sharedDocs || [];
        if (docs.length === 0) {
            this.notification.add("No documents have been shared with you yet.", { type: "info" });
            return;
        }
        if (docs.length === 1) {
            return this.openDocument(docs[0].id);
        }
        this.state.sharedPopup = { open: true };
    }

    closeSharedPopup() {
        this.state.sharedPopup = { open: false };
    }

    openSharedDoc(id) {
        this.closeSharedPopup();
        this.openDocument(id);
    }

    async onRefresh() {
        await this.loadSummary();
        await this.loadFolder(this.state.currentFolderId);
        this.notification.add("Dashboard refreshed.", { type: "success" });
    }

    // ------------------------------------------------------------------
    // Derived data
    // ------------------------------------------------------------------
    get filteredSidebar() {
        const term = (this.state.sideSearch || "").trim().toLowerCase();
        if (!term) {
            return this.state.folders;
        }
        return this.state.folders.filter((f) =>
            (f.name || "").toLowerCase().includes(term)
        );
    }

    get items() {
        const folders = (this.state.subfolders || []).map((f) => ({
            kind: "folder", id: f.id, name: f.name, count: f.count,
        }));
        const docs = (this.state.documents || []).map((d) => ({
            kind: "doc", ...d,
        }));
        return [...folders, ...docs];
    }

    get filteredItems() {
        let list = this.items;
        if (this.state.activeTab === "files") {
            list = list.filter((i) => i.kind === "doc");
        }
        const term = (this.state.search || "").trim().toLowerCase();
        if (term) {
            list = list.filter((i) => (i.name || "").toLowerCase().includes(term));
        }
        return list;
    }

    get totalPages() {
        return Math.max(1, Math.ceil(this.filteredItems.length / PAGE_SIZE));
    }

    get pagedItems() {
        const start = (this.state.page - 1) * PAGE_SIZE;
        return this.filteredItems.slice(start, start + PAGE_SIZE);
    }

    get rangeStart() {
        return this.filteredItems.length === 0 ? 0 : (this.state.page - 1) * PAGE_SIZE + 1;
    }

    get rangeEnd() {
        return Math.min(this.state.page * PAGE_SIZE, this.filteredItems.length);
    }

    colorFor(index) {
        return FOLDER_PALETTE[index % FOLDER_PALETTE.length];
    }

    extColor(ext) {
        return EXT_COLORS[(ext || "").toLowerCase()] || "#6366f1";
    }

    iconFor(ext) {
        return EXT_ICONS[(ext || "").toLowerCase()] || "fa-file-o";
    }

    // ------------------------------------------------------------------
    // Tabs / pagination
    // ------------------------------------------------------------------
    onTab(tab) {
        if (tab === "shared") {
            return this.openCard("shared");
        }
        this.state.activeTab = tab;
        this.state.page = 1;
    }

    prevPage() {
        if (this.state.page > 1) {
            this.state.page -= 1;
        }
    }

    nextPage() {
        if (this.state.page < this.totalPages) {
            this.state.page += 1;
        }
    }

    // ------------------------------------------------------------------
    // Navigation
    // ------------------------------------------------------------------
    openFolder(folderId) {
        this.loadFolder(folderId);
    }

    goHome() {
        this.loadFolder(false);
    }

    goCrumb(folderId) {
        this.loadFolder(folderId);
    }

    // ------------------------------------------------------------------
    // Kebab menu
    // ------------------------------------------------------------------
    toggleMenu(item, ev) {
        // Toggle off if the same card's menu is already open.
        if (this.state.menu.open && this.state.menu.id === item.id) {
            this.state.menu.open = false;
            return;
        }
        const rect = ev.currentTarget.getBoundingClientRect();
        const width = 200;
        const height = item.is_pdf ? 232 : 196;
        let left = rect.right - width;
        if (left < 8) {
            left = 8;
        }
        let top = rect.bottom + 6;
        if (top + height > window.innerHeight - 8) {
            top = rect.top - height - 6;
            if (top < 8) {
                top = 8;
            }
        }
        this.state.menu = {
            open: true,
            x: Math.round(left),
            y: Math.round(top),
            id: item.id,
            isPdf: !!item.is_pdf,
        };
    }

    closeMenu() {
        this.state.menu.open = false;
    }

    // ------------------------------------------------------------------
    // Document actions
    // ------------------------------------------------------------------
    async toggleFavorite(item, ev) {
        if (ev) { ev.stopPropagation(); }
        const newVal = !item.is_favorite;
        item.is_favorite = newVal;
        try {
            await this.orm.write("edm.document", [item.id], { is_favorite: newVal });
        } catch (e) {
            item.is_favorite = !newVal;
            this.notification.add("Could not update favorite.", { type: "danger" });
        }
    }

    async openDocument(docId) {
        this.closeMenu();
        let r = {};
        try {
            const recs = await this.orm.read("edm.document", [docId], ["name", "file_name", "file_extension", "can_annotate", "can_download"]);
            r = (recs && recs[0]) || {};
        } catch { r = {}; }
        const ext = (r.file_extension || "").toLowerCase();
        this.state.popup = { open: true, id: docId, name: r.name || r.file_name || "Document", ext: ext, isPdf: ext === "pdf", isImage: ["png","jpg","jpeg","gif","webp","bmp","svg"].includes(ext), preview: ext === "pdf", canAnnotate: !!r.can_annotate, canDownload: !!r.can_download };
    }

    closePopup() {
        this.state.popup = { open: false, id: null, name: "", ext: "", isPdf: false, isImage: false, preview: false, canAnnotate: false, canDownload: false };
    }

    togglePreview() {
        this.state.popup.preview = !this.state.popup.preview;
    }

    onPreviewLoad(ev) {
        try {
            const doc = ev.target.contentDocument;
            if (!doc) return;
            const css = [
                "#downloadButton,#download,#secondaryDownload{display:none !important}",
                "#editorModeButtons,#editorModeSeparator,#editorFreeText,#editorInk,#editorStamp,#editorHighlight,#editorFreeTextButton,#editorInkButton,#editorStampButton,#editorHighlightButton{display:none !important}",
                "#toolbarContainer,#toolbarViewer,.toolbar{background:#ffffff !important;border-bottom:1px solid #eef0f6 !important;box-shadow:none !important}",
                ".toolbarButton,.dropdownToolbarButton,.secondaryToolbarButton{color:#3a3f4b !important}",
                ".toolbarButton:hover,.dropdownToolbarButton:hover,#zoomIn:hover,#zoomOut:hover{background:#eef0fb !important;border-radius:8px !important}",
                "#scaleSelect,#pageNumber{border:1px solid #e4e6ef !important;border-radius:7px !important}",
                "#viewerContainer{background:#f7f8fa !important}"
            ].join("");
            const st = doc.createElement("style");
            st.textContent = css;
            (doc.head || doc.documentElement).appendChild(st);
        } catch (e) {
        }
    }

    get previewUrl() {
        const id = this.state.popup.id;
        if (!id) return "";
        return "/edm/document/preview/" + id + "#toolbar=1&navpanes=0&zoom=page-width";
    }

    get imageUrl() {
        const id = this.state.popup.id;
        if (!id) return "";
        return "/edm/document/preview/" + id;
    }

    popupAnnotate() {
        const id = this.state.popup.id;
        this.closePopup();
        this.annotateDoc(id);
    }

    popupDownload() {
        this.downloadDoc(this.state.popup.id);
    }

    popupForm() {
        const id = this.state.popup.id;
        this.closePopup();
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "edm.document",
            res_id: id,
            views: [[false, "form"]],
            target: "current",
        });
    }

    async downloadDoc(docId) {
        this.closeMenu();
        try {
            const action = await this.orm.call(
                "edm.document", "action_download_document", [docId]
            );
            if (action) {
                this.action.doAction(action);
            }
        } catch {
            this.notification.add("Unable to download this document.", { type: "danger" });
        }
    }

    shareDoc(docId) {
        this.closeMenu();
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Share Document",
            res_model: "edm.document.share.wizard",
            views: [[false, "form"]],
            target: "new",
            context: { default_document_id: docId },
        });
    }

    requestApproval(docId) {
        this.closeMenu();
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Request Approval",
            res_model: "edm.document.request.wizard",
            views: [[false, "form"]],
            target: "new",
            context: { default_document_id: docId },
        });
    }

    async annotateDoc(docId) {
        this.closeMenu();
        try {
            // Read the file and open the annotator overlay ON THIS PAGE
            // (no navigation to a separate action/page).
            const recs = await this.orm.read(
                "edm.document", [docId], ["file", "file_name", "file_extension"]
            );
            const rec = recs && recs[0];
            if (!rec || !rec.file) {
                this.notification.add("No PDF file found for annotation.", { type: "warning" });
                return;
            }
            await openAnnotator(docId, rec.file, rec.file_name || "document.pdf");
        } catch {
            this.notification.add("Unable to open the PDF annotator.", { type: "danger" });
        }
    }

    // ------------------------------------------------------------------
    // Stat-card navigation
    // ------------------------------------------------------------------
    _openDocuments(domain, name) {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: name,
            res_model: "edm.document",
            views: [[false, "kanban"], [false, "list"], [false, "form"]],
            domain: domain,
            target: "current",
            context: { create: false },
        });
    }

    openCard(kind) {
        const notTrashed = ["is_trashed", "=", false];
        const uid = session.uid;
        switch (kind) {
            case "my":
                return this._openDocuments([notTrashed, ["owner_id", "=", uid]], "My Documents");
            case "shared":
                // Open shared-with-me documents in a popup on THIS page
                // (no navigation to a separate list/form page).
                return this.openSharedPopup();
            case "review":
                return this.action.doAction({
                    type: "ir.actions.act_window",
                    name: "Need My Review",
                    res_model: "edm.document.request",
                    views: [[false, "list"], [false, "form"]],
                    domain: [["requested_to", "=", uid], ["state", "=", "requested"]],
                    target: "current",
                });
            case "pending":
                return this.action.doAction({
                    type: "ir.actions.act_window",
                    name: "Pending With Others",
                    res_model: "edm.document.request",
                    views: [[false, "list"], [false, "form"]],
                    domain: [["requested_by", "=", uid], ["state", "=", "requested"]],
                    target: "current",
                });
        }
    }

    openAllDocuments() {
        this._openDocuments([["is_trashed", "=", false]], "All Documents");
    }

    // ------------------------------------------------------------------
    // Quick actions
    // ------------------------------------------------------------------
    openUpload() {
        this.action.doAction("inom_advance_dms.action_edm_dropzone_upload");
    }

    openNewRequest() {
        this.action.doAction("inom_advance_dms.action_edm_document_request_wizard");
    }

    openNewFolder() {
        const context = {};
        if (this.state.currentFolderId) {
            context.default_parent_id = this.state.currentFolderId;
        }
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "New Folder",
            res_model: "edm.folder",
            views: [[false, "form"]],
            target: "new",
            context: context,
        }, { onClose: () => this.loadSummary() });
    }

    // ------------------------------------------------------------------
    // Drag & drop upload
    // ------------------------------------------------------------------
    onDragEnter() {
        this._dragDepth = (this._dragDepth || 0) + 1;
        this.state.dragActive = true;
    }

    onDragOver(ev) {
        if (ev.dataTransfer) { ev.dataTransfer.dropEffect = "copy"; }
    }

    onDragLeave() {
        this._dragDepth = (this._dragDepth || 1) - 1;
        if (this._dragDepth <= 0) { this._dragDepth = 0; this.state.dragActive = false; }
    }

    async onDrop(ev) {
        this._dragDepth = 0;
        this.state.dragActive = false;
        const files = ev.dataTransfer && ev.dataTransfer.files
            ? Array.from(ev.dataTransfer.files)
            : [];
        if (files.length) {
            await this.uploadFiles(files);
        }
    }

    async uploadFiles(files) {
        this.state.uploading = true;
        let ok = 0;
        let fail = 0;
        for (const file of files) {
            const form = new FormData();
            form.append("ufile", file);
            form.append("name", file.name);
            if (this.state.currentFolderId) {
                form.append("folder_id", this.state.currentFolderId);
            }
            try {
                const resp = await fetch("/edm/upload/dropzone", {
                    method: "POST",
                    body: form,
                });
                const data = await resp.json();
                if (data && data.status === "ok") {
                    ok += 1;
                } else {
                    fail += 1;
                    if (data && data.message) {
                        this.notification.add(data.message, { type: "warning" });
                    }
                }
            } catch {
                fail += 1;
            }
        }
        this.state.uploading = false;
        if (ok) {
            this.notification.add(`${ok} file(s) uploaded.`, { type: "success" });
        }
        if (fail) {
            this.notification.add(`${fail} file(s) could not be uploaded.`, { type: "danger" });
        }
        await this.loadSummary();
        await this.loadFolder(this.state.currentFolderId);
    }
}

registry.category("actions").add("edm_dashboard_pro", EdmDashboard);
