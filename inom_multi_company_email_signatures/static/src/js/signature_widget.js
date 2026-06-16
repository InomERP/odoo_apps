/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, onMounted, useRef, useState } from "@odoo/owl";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

export class InomSignatureWidget extends Component {
    static template = "inom_multi_company_email_signatures.SignatureWidget";
    static props = { ...standardFieldProps };

    setup() {
        this.canvasRef = useRef("canvas");
        this._canvasListenersAttached = false;

        const savedValue = this.props.record.data[this.props.name] || "";

        // Detect tab strictly from prefix
        let initialTab = "draw";
        if (savedValue.startsWith("typed:")) {
            initialTab = "type";
        } else if (savedValue.startsWith("upload:")) {
            initialTab = "upload";
        } else {
            initialTab = "draw";  // draw: prefix OR bare data:image OR empty
        }

        // Strip prefix to get clean base64
        const strippedValue = this._stripPrefix(savedValue);

        // Only set previewSrc for type/upload tabs
        // Draw tab uses canvas restore — previewSrc causes cross-tab leakage
        this.state = useState({
            activeTab: initialTab,
            drawnOnce: false,
            previewSrc: (initialTab === "type" || initialTab === "upload") ? strippedValue : "",
            typedText: "",
        });
        this.switchTab      = this.switchTab.bind(this);
        this.onTyped        = this.onTyped.bind(this);
        this.onUpload       = this.onUpload.bind(this);
        this.clearSignature = this.clearSignature.bind(this);

        onMounted(() => {
            const existing = this.props.record.data[this.props.name] || "";
            const stripped = this._stripPrefix(existing);

            if (initialTab === "draw") {
                this._initCanvas();
                if (stripped && stripped.startsWith("data:image")) {
                    setTimeout(() => this._restoreToCanvas(stripped), 60);
                }
            } else if (initialTab === "type") {
                this.state.previewSrc = stripped;
            } else if (initialTab === "upload") {
                this.state.previewSrc = stripped;
            }
        });
    }

    _stripPrefix(val) {
        return (val || "")
            .replace(/^draw:/, "")
            .replace(/^typed:/, "")
            .replace(/^upload:/, "");
    }

    _initCanvas() {
        if (this._canvasListenersAttached) return;
        const canvas = this.canvasRef.el;
        if (!canvas) return;

        this._canvasListenersAttached = true;

        const ctx = canvas.getContext("2d");
        ctx.fillStyle = "#fff";
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        ctx.strokeStyle = "#1e293b";
        ctx.lineWidth = 2.4;
        ctx.lineCap = "round";
        ctx.lineJoin = "round";

        let drawing = false, lx = 0, ly = 0;
        const self = this;

        const pt = (e) => {
            const r  = canvas.getBoundingClientRect();
            const sx = canvas.width  / r.width;
            const sy = canvas.height / r.height;
            const src = e.touches ? e.touches[0] : e;
            return {
                x: (src.clientX - r.left) * sx,
                y: (src.clientY - r.top)  * sy,
            };
        };

        const start = (e) => {
            drawing = true;
            const p = pt(e);
            lx = p.x; ly = p.y;
            e.preventDefault();
        };

        const move = (e) => {
            if (!drawing) return;
            const p = pt(e);
            ctx.beginPath();
            ctx.moveTo(lx, ly);
            ctx.lineTo(p.x, p.y);
            ctx.stroke();
            lx = p.x; ly = p.y;
            self.state.drawnOnce = true;
            e.preventDefault();
        };

        const end = () => {
            if (!drawing) return;
            drawing = false;
            if (self.state.drawnOnce) self._saveFromCanvas();
        };

        canvas.addEventListener("mousedown",  start);
        canvas.addEventListener("mousemove",  move);
        canvas.addEventListener("mouseup",    end);
        canvas.addEventListener("mouseleave", end);
        canvas.addEventListener("touchstart", start, { passive: false });
        canvas.addEventListener("touchmove",  move,  { passive: false });
        canvas.addEventListener("touchend",   end);
    }

    _saveFromCanvas() {
        const canvas = this.canvasRef.el;
        if (!canvas) return;
        const dataUrl = canvas.toDataURL("image/png");
        this.state.previewSrc = dataUrl;
        this.props.record.update({ [this.props.name]: "draw:" + dataUrl });
    }

    _restoreToCanvas(val) {
        const src = this._stripPrefix(val);
        if (!src || !src.startsWith("data:image")) return;
        const canvas = this.canvasRef.el;
        if (!canvas) return;
        const ctx = canvas.getContext("2d");
        const img = new Image();
        img.onload = () => {
            const r = Math.min(canvas.width / img.width, canvas.height / img.height);
            const w = img.width * r, h = img.height * r;
            ctx.fillStyle = "#fff";
            ctx.fillRect(0, 0, canvas.width, canvas.height);
            ctx.drawImage(img,
                (canvas.width  - w) / 2,
                (canvas.height - h) / 2,
                w, h
            );
        };
        img.src = src;
    }

    switchTab(mode) {
        this._canvasListenersAttached = false;
        this.state.activeTab = mode;
        if (mode === "draw") {
            setTimeout(() => {
                this._initCanvas();
                const existing = this.props.record.data[this.props.name] || "";
                if (existing.startsWith("draw:")) {
                    this._restoreToCanvas(existing);
                }
            }, 80);
        }
    }

    onTyped(ev) {
        const text = (ev.target.value || "").trim();
        this.state.typedText = ev.target.value || "";
        if (!text) {
            this.state.previewSrc = "";
            this.props.record.update({ [this.props.name]: "" });
            return;
        }
        const c = document.createElement("canvas");
        c.width = 600; c.height = 140;
        const cx = c.getContext("2d");
        cx.fillStyle = "#fff";
        cx.fillRect(0, 0, c.width, c.height);
        cx.fillStyle = "#1e293b";
        cx.font = "italic 56px 'Brush Script MT','Lucida Handwriting',cursive";
        cx.textBaseline = "middle";
        cx.textAlign = "left";
        cx.fillText(text, 24, c.height / 2);
        const dataUrl = c.toDataURL("image/png");
        this.state.previewSrc = dataUrl;
        this.props.record.update({ [this.props.name]: "typed:" + dataUrl });
    }

    onUpload(ev) {
        const file = ev.target.files && ev.target.files[0];
        if (!file) return;
        const reader = new FileReader();
        const self = this;
        reader.onload = (e) => {
            self.state.previewSrc = e.target.result;
            self.props.record.update({
                [self.props.name]: "upload:" + e.target.result,
            });
        };
        reader.readAsDataURL(file);
    }

    clearSignature() {
        const canvas = this.canvasRef.el;
        if (canvas) {
            const ctx = canvas.getContext("2d");
            ctx.fillStyle = "#fff";
            ctx.fillRect(0, 0, canvas.width, canvas.height);
        }
        this._canvasListenersAttached = false;
        this.state.drawnOnce  = false;
        this.state.previewSrc = "";
        this.state.typedText  = "";
        this.props.record.update({ [this.props.name]: "" });
    }

    get currentValue() {
        return this.props.record.data[this.props.name] || "";
    }

    get hasSavedValue() {
        return (this.props.record.data[this.props.name] || "").length > 0;
    }

    get displaySrc() {
        // Only return previewSrc — never fall back to currentValue
        // This prevents draw signature leaking into type/upload tabs
        const v = this.state.previewSrc || "";
        return v.startsWith("data:image") ? v : "";
    }
}

registry.category("fields").add("inom_signature", {
    component: InomSignatureWidget,
    displayName: "Inom Signature",
    supportedTypes: ["text", "char"],
});