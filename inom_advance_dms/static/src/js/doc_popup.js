/** @odoo-module **/
import { registry } from "@web/core/registry";
import { Component, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { Dialog } from "@web/core/dialog/dialog";
import { openAnnotator } from "./pdf_annotator";

export class DocPopupBody extends Component {
    setup() {
        this.state = useState({ preview: this.props.isPdf });
        this.orm = useService("orm");
    }
    get previewUrl() {
        return "/web/content/edm.document/" + this.props.docId + "/file#toolbar=1";
    }
    togglePreview() {
        this.state.preview = !this.state.preview;
    }
    download() {
        window.location.href = "/web/content/edm.document/" + this.props.docId + "/file?download=true";
    }
    async annotate() {
        try {
            const recs = await this.orm.read("edm.document", [this.props.docId], ["file", "name"]);
            const r = (recs && recs[0]) || {};
            if (this.props.close) { this.props.close(); }
            if (r.file) { openAnnotator(this.props.docId, r.file, r.name || this.props.name); }
        } catch (e) {
            console.error(e);
        }
    }
}
DocPopupBody.template = "inom_advance_dms.DocPopupBody";
DocPopupBody.components = { Dialog };
DocPopupBody.props = ["docId", "name", "isPdf", "ext", "close?"];

export class EdmDocPopupWidget extends Component {
    setup() {
        this.dialog = useService("dialog");
    }
    get rec() {
        return this.props.record.data;
    }
    iconClass() {
        const e = (this.rec.file_extension || "").toLowerCase();
        if (e === "pdf") return "fa fa-file-pdf-o";
        if (e === "xls" || e === "xlsx") return "fa fa-file-excel-o";
        if (e === "doc" || e === "docx") return "fa fa-file-word-o";
        if (["png", "jpg", "jpeg"].includes(e)) return "fa fa-file-image-o";
        if (e === "url") return "fa fa-link";
        return "fa fa-file-o";
    }

    iconColor() {
        const e = (this.rec.file_extension || "").toLowerCase();
        const map = {
            pdf: "#f43f5e",
            doc: "#3b82f6", docx: "#3b82f6",
            xls: "#10b981", xlsx: "#10b981", csv: "#14b8a6",
            ppt: "#ea580c", pptx: "#ea580c",
            png: "#8b5cf6", jpg: "#8b5cf6", jpeg: "#8b5cf6",
            gif: "#8b5cf6", svg: "#8b5cf6", webp: "#8b5cf6",
            txt: "#64748b", zip: "#f59e0b", url: "#06b6d4",
        };
        return map[e] || "#6366f1";
    }
    open(ev) {
        if (ev) {
            ev.stopPropagation();
            if (ev.stopImmediatePropagation) { ev.stopImmediatePropagation(); }
            ev.preventDefault();
        }
        const e = (this.rec.file_extension || "").toLowerCase();
        this.dialog.add(DocPopupBody, {
            docId: this.props.record.resId,
            name: this.rec.name || "Document",
            isPdf: e === "pdf",
            ext: e,
        });
    }
}
EdmDocPopupWidget.template = "inom_advance_dms.DocPopupWidget";
EdmDocPopupWidget.props = ["*"];

registry.category("view_widgets").add("edm_doc_popup", { component: EdmDocPopupWidget });
