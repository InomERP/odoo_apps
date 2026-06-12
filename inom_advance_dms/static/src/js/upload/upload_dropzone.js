/** @odoo-module **/
import { Component, useState, useRef, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

const ALLOWED_EXTENSIONS = [
    "pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx",
    "txt", "rtf", "csv", "odt", "ods", "odp", "md",
    "png", "jpg", "jpeg", "gif", "bmp", "svg", "webp", "tiff", "tif", "ico", "heic",
    "zip", "rar", "7z", "tar", "gz",
    "mp3", "wav", "ogg", "m4a", "flac",
    "mp4", "avi", "mov", "mkv", "webm", "wmv",
    "json", "xml", "html", "htm", "yaml", "yml",
];
const MAX_FILE_SIZE = 100 * 1024 * 1024;

let _uid = 0;

export class EdmUploadDropzone extends Component {
    static template = "inom_advance_dms.UploadDropzone";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
        this.fileInput = useRef("fileInput");

        this.state = useState({
            files: [],
            dragging: false,
            uploading: false,
            workspaceId: false,
            workspaces: [],
            isFavorite: false,
            documentName: "",
            fileName: "",
            documentName: "",
            fileName: "",
            done: 0,
            failed: 0,
        });

        onWillStart(async () => {
            try {
                this.state.workspaces = await this.orm.searchRead(
                    "edm.workspace", [], ["id", "name"], { order: "name" }
                );
            } catch {
                this.state.workspaces = [];
            }
        });
    }

    _extension(name) {
        return name && name.includes(".") ? name.split(".").pop().toLowerCase() : "";
    }

    humanSize(bytes) {
        if (!bytes) return "0 B";
        const units = ["B", "KB", "MB", "GB"];
        let size = bytes, i = 0;
        while (size >= 1024 && i < units.length - 1) { size /= 1024; i++; }
        return (i === 0 ? size : size.toFixed(1)) + " " + units[i];
    }

    iconFor(ext) {
        const map = {
            pdf: "fa-file-pdf-o", doc: "fa-file-word-o", docx: "fa-file-word-o",
            xls: "fa-file-excel-o", xlsx: "fa-file-excel-o",
            png: "fa-file-image-o", jpg: "fa-file-image-o", jpeg: "fa-file-image-o",
            txt: "fa-file-text-o", zip: "fa-file-archive-o",
        };
        return map[ext] || "fa-file-o";
    }

    get hasPending() {
        return this.state.files.some((f) => f.status === "pending");
    }

    get acceptAttr() {
        return ALLOWED_EXTENSIONS.map((e) => "." + e).join(",");
    }

    onDragOver(ev) { ev.preventDefault(); this.state.dragging = true; }
    onDragLeave(ev) { ev.preventDefault(); this.state.dragging = false; }

    onDrop(ev) {
        ev.preventDefault();
        this.state.dragging = false;
        const files = ev.dataTransfer && ev.dataTransfer.files;
        if (files && files.length) this.addFiles(files);
    }

    onBrowseClick() {
        if (this.fileInput.el) this.fileInput.el.click();
    }

    onFileInputChange(ev) {
        const files = ev.target.files;
        if (files && files.length) this.addFiles(files);
        ev.target.value = "";
    }

    addFiles(fileList) {
        for (const file of fileList) {
            const ext = this._extension(file.name);
            const dup = this.state.files.some((f) => f.name === file.name && f.size === file.size);
            if (dup) {
                this.notification.add(`"${file.name}" is already in the list.`, { type: "warning" });
                continue;
            }
            let error = false, status = "pending";
            if (!ALLOWED_EXTENSIONS.includes(ext)) {
                error = `Unsupported format (.${ext || "?"})`;
                status = "invalid";
            } else if (file.size > MAX_FILE_SIZE) {
                error = "File too large (max 25 MB)";
                status = "invalid";
            } else if (file.size === 0) {
                error = "Empty file";
                status = "invalid";
            }
            this.state.files.push({
                uid: ++_uid, name: file.name, size: file.size,
                ext, status, progress: 0, error, raw: file,
            });
        }
    }

    removeFile(uid) {
        const idx = this.state.files.findIndex((f) => f.uid === uid);
        if (idx !== -1) this.state.files.splice(idx, 1);
    }

    clearAll() {
        if (this.state.uploading) return;
        this.state.files = [];
        this.state.done = 0;
        this.state.failed = 0;
    }

    _uploadOne(entry) {
        return new Promise((resolve) => {
            const formData = new FormData();
            formData.append("ufile", entry.raw, entry.name);
            formData.append("name", this.state.documentName || entry.name);
            formData.append("file_name", this.state.fileName || entry.name);
            formData.append("is_favorite", this.state.isFavorite ? "1" : "0");
            if (this.state.workspaceId) formData.append("workspace_id", this.state.workspaceId);

            const xhr = new XMLHttpRequest();
            xhr.open("POST", "/edm/upload/dropzone", true);

            xhr.upload.onprogress = (e) => {
                if (e.lengthComputable) entry.progress = Math.round((e.loaded / e.total) * 100);
            };

            xhr.onload = () => {
                let payload = {};
                try { payload = JSON.parse(xhr.responseText); }
                catch { payload = { status: "error", message: "Invalid server response" }; }
                if (xhr.status === 200 && payload.status === "ok") {
                    entry.progress = 100;
                    entry.status = "done";
                    entry.duplicate = !!payload.duplicate;
                    resolve(true);
                } else {
                    entry.status = "error";
                    entry.error = payload.message || "Upload failed";
                    resolve(false);
                }
            };

            xhr.onerror = () => { entry.status = "error"; entry.error = "Network error"; resolve(false); };
            entry.status = "uploading";
            entry.progress = 0;
            xhr.send(formData);
        });
    }

    async uploadAll() {
        const pending = this.state.files.filter((f) => f.status === "pending");
        if (!pending.length || this.state.uploading) return;

        this.state.uploading = true;
        this.state.done = 0;
        this.state.failed = 0;

        for (const entry of pending) {
            const ok = await this._uploadOne(entry);
            if (ok) this.state.done++; else this.state.failed++;
        }

        this.state.uploading = false;

        if (this.state.done) this.notification.add(`${this.state.done} file(s) uploaded successfully.`, { type: "success" });
        if (this.state.failed) this.notification.add(`${this.state.failed} file(s) failed to upload.`, { type: "danger" });
    }

    openDocuments() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Documents",
            res_model: "edm.document",
            views: [[false, "kanban"], [false, "list"], [false, "form"]],
            domain: [["is_trashed", "=", false]],
            target: "current",
        });
    }
}

registry.category("actions").add("edm_dropzone_upload", EdmUploadDropzone);
