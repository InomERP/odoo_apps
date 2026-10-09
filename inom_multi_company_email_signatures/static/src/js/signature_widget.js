import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { Component, proxy, signal, useListener, useOnChange, useProps } from "@odoo/owl";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

export class InomSignatureWidget extends Component {
    static template = "inom_multi_company_email_signatures.SignatureWidget";
    props = useProps(standardFieldProps);
    canvasRef = signal.ref();

    setup() {
        const savedValue = this.currentValue;

        // Detect tab strictly from prefix
        let initialTab = "draw";
        if (savedValue.startsWith("typed:")) {
            initialTab = "type";
        } else if (savedValue.startsWith("upload:")) {
            initialTab = "upload";
        } else {
            initialTab = "draw";  // draw: prefix OR bare data:image OR empty
        }

        // Only set previewSrc for type/upload tabs
        // Draw tab uses canvas restore — previewSrc causes cross-tab leakage
        this.state = proxy({
            activeTab: initialTab,
            drawnOnce: false,
            previewSrc: (initialTab === "type" || initialTab === "upload")
                ? this._stripPrefix(savedValue) : "",
            typedText: "",
        });

        this._drawing = false;
        this._lx = 0;
        this._ly = 0;

        // The canvas only exists while the Draw tab is active: (re)initialise
        // it every time it is mounted, and restore the saved drawing if any.
        useOnChange(() => [this.canvasRef()], (canvas) => {
            if (!canvas) return;
            this._initCanvas(canvas);
            const existing = this.currentValue;
            if (!existing.startsWith("typed:") && !existing.startsWith("upload:")) {
                this._restoreToCanvas(existing);
            }
        });

        // Listeners are attached/detached automatically with the canvas element
        useListener(this.canvasRef, "mousedown",  (e) => this._start(e));
        useListener(this.canvasRef, "mousemove",  (e) => this._move(e));
        useListener(this.canvasRef, "mouseup",    () => this._end());
        useListener(this.canvasRef, "mouseleave", () => this._end());
        useListener(this.canvasRef, "touchstart", (e) => this._start(e), { passive: false });
        useListener(this.canvasRef, "touchmove",  (e) => this._move(e),  { passive: false });
        useListener(this.canvasRef, "touchend",   () => this._end());
    }

    _stripPrefix(val) {
        return (val || "")
            .replace(/^draw:/, "")
            .replace(/^typed:/, "")
            .replace(/^upload:/, "");
    }

    _initCanvas(canvas) {
        const ctx = canvas.getContext("2d");
        ctx.fillStyle = "#fff";
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        ctx.strokeStyle = "#1e293b";
        ctx.lineWidth = 2.4;
        ctx.lineCap = "round";
        ctx.lineJoin = "round";
    }

    _point(e) {
        const canvas = this.canvasRef();
        const r  = canvas.getBoundingClientRect();
        const sx = canvas.width  / r.width;
        const sy = canvas.height / r.height;
        const src = e.touches ? e.touches[0] : e;
        return {
            x: (src.clientX - r.left) * sx,
            y: (src.clientY - r.top)  * sy,
        };
    }

    _start(e) {
        if (this.props.readonly) return;
        this._drawing = true;
        const p = this._point(e);
        this._lx = p.x; this._ly = p.y;
        e.preventDefault();
    }

    _move(e) {
        if (!this._drawing) return;
        const ctx = this.canvasRef().getContext("2d");
        const p = this._point(e);
        ctx.beginPath();
        ctx.moveTo(this._lx, this._ly);
        ctx.lineTo(p.x, p.y);
        ctx.stroke();
        this._lx = p.x; this._ly = p.y;
        this.state.drawnOnce = true;
        e.preventDefault();
    }

    _end() {
        if (!this._drawing) return;
        this._drawing = false;
        if (this.state.drawnOnce) this._saveFromCanvas();
    }

    _saveFromCanvas() {
        const canvas = this.canvasRef();
        if (!canvas) return;
        const dataUrl = canvas.toDataURL("image/png");
        this.state.previewSrc = dataUrl;
        this.props.record.update({ [this.props.name]: "draw:" + dataUrl });
    }

    _restoreToCanvas(val) {
        const src = this._stripPrefix(val);
        if (!src || !src.startsWith("data:image")) return;
        const img = new Image();
        img.onload = () => {
            // The draw tab may have been left before the image finished loading
            const canvas = this.canvasRef();
            if (!canvas) return;
            const ctx = canvas.getContext("2d");
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
        this.state.activeTab = mode;
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
        reader.onload = (e) => {
            this.state.previewSrc = e.target.result;
            this.props.record.update({
                [this.props.name]: "upload:" + e.target.result,
            });
        };
        reader.readAsDataURL(file);
    }

    clearSignature() {
        const canvas = this.canvasRef();
        if (canvas) {
            const ctx = canvas.getContext("2d");
            ctx.fillStyle = "#fff";
            ctx.fillRect(0, 0, canvas.width, canvas.height);
        }
        this.state.drawnOnce  = false;
        this.state.previewSrc = "";
        this.state.typedText  = "";
        this.props.record.update({ [this.props.name]: "" });
    }

    get currentValue() {
        return this.props.record.data[this.props.name] || "";
    }

    get hasSavedValue() {
        return this.currentValue.length > 0;
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
    displayName: _t("Inom Signature"),
    supportedTypes: ["text", "char"],
});
