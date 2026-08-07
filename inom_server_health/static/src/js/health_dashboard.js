/** @odoo-module **/

import {
    Component, onMounted, onWillStart, onWillUnmount, useRef, useState,
} from "@odoo/owl";
import { registry } from "@web/core/registry";
import { browser } from "@web/core/browser/browser";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

/**
 * Polling policy -- this is what decides whether the dashboard is harmless or
 * a permanent load source.
 *
 *  1. setTimeout chain, never setInterval. A slow response must not let the
 *     next request fire on top of it.
 *  2. Paused whenever the tab is hidden. A forgotten background tab is the
 *     usual way monitoring dashboards quietly consume a worker forever.
 *  3. Exponential backoff on failure, capped. A restarting server should not
 *     be hammered by every open dashboard at full rate.
 *  4. Interval is server-configured and floored, so it cannot be set to
 *     something pathological.
 */
const MIN_INTERVAL_MS = 3000;
const MAX_BACKOFF_MS = 120000;

/**
 * The trace plots against TIME, not sample index.
 *
 * This matters: cron history arrives one point per minute, the live feed
 * arrives one point per poll (10 s by default). Plotting those at equal
 * spacing would draw a chart labelled "last 60 minutes" whose left half was
 * really the last few minutes. Every point therefore carries its own
 * timestamp and is positioned by it.
 */
const WINDOW_MS = 60 * 60 * 1000;
/** Hard cap on retained points, so a long-lived tab cannot grow unbounded. */
const MAX_POINTS = 900;
/** Fine-grained live points survive a page refresh here. Cron history alone
 *  is one point per minute; this keeps the detail you were watching. */
const STORAGE_KEY = "inom_server_health.trace";

const CHANNELS = [
    { key: "cpu", label: _t("CPU"), varName: "--inom-ch-cpu" },
    { key: "mem", label: _t("Memory"), varName: "--inom-ch-mem" },
    { key: "db", label: _t("DB conn"), varName: "--inom-ch-db" },
    { key: "load", label: _t("Load"), varName: "--inom-ch-load" },
];

export class ServerHealthDashboard extends Component {
    static template = "inom_server_health.Dashboard";
    // Client actions receive action/actionId/className/updateActionState from
    // the action service. Owl's props schema must be an array or object --
    // the bare string "*" makes validateSchema do `'action' in "*"` and throw.
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.canvasRef = useRef("chart");
        this.channels = CHANNELS.map((c) => ({ ...c, on: true, color: "#888" }));

        this.state = useState({
            data: null,
            loading: true,
            error: null,
            paused: false,
            intervalMs: 10000,
            latest: { cpu: null, mem: null, db: null, load: null },
            channelsOn: { cpu: true, mem: true, db: true, load: true },
            manualPause: false,
            demo: false,
        });

        // The ring buffers are deliberately NOT reactive. They hold up to 180
        // points per channel and are consumed by imperative canvas drawing;
        // putting them in useState would re-render everything on every poll
        // for no benefit.
        // Each entry is {t: epochMs, v: percent}. Deliberately NOT reactive:
        // these hold hundreds of points and are drawn imperatively.
        this.points = Object.fromEntries(CHANNELS.map((c) => [c.key, []]));

        this._timer = null;
        this._stopped = false;
        this._failures = 0;
        this._resizeObserver = null;
        this._gridColor = "#eee";
        this._edgeColor = "#ddd";
        this._faintColor = "#999";

        onWillStart(async () => {
            this.state.demo = new URLSearchParams(
                browser.location.search).get("health_demo") === "1";
            this._restoreLocal();
            await this._loadInterval();
            await this._loadSeed();
        });

        onMounted(() => {
            this._readChannelColors();
            this._resize();
            if (browser.ResizeObserver && this.canvasRef.el) {
                this._resizeObserver = new browser.ResizeObserver(() => {
                    this._resize();
                    this._draw();
                });
                this._resizeObserver.observe(this.canvasRef.el);
            }
            this._draw();
            // Not awaited: the shell is painted already, fill it when data lands.
            this._tick();
        });

        this._onVisibility = () => {
            if (document.visibilityState === "hidden") {
                this.state.paused = true;
                this._clearTimer();
            } else if (this.state.paused) {
                this.state.paused = false;
                this._tick();
            }
        };
        document.addEventListener("visibilitychange", this._onVisibility);

        onWillUnmount(() => {
            this._stopped = true;
            this._clearTimer();
            if (this._resizeObserver) {
                this._resizeObserver.disconnect();
            }
            document.removeEventListener("visibilitychange", this._onVisibility);
        });
    }

    // ----- setup ---------------------------------------------------------

    _readChannelColors() {
        // Colours live in SCSS so the theme owns them; the canvas has to ask.
        const root = this.canvasRef.el
            && this.canvasRef.el.closest(".o_inom_health");
        if (!root) {
            return;
        }
        const styles = getComputedStyle(root);
        for (const channel of this.channels) {
            const value = styles.getPropertyValue(channel.varName).trim();
            if (value) {
                channel.color = value;
            }
        }
        this._gridColor =
            styles.getPropertyValue("--inom-rule-soft").trim() || this._gridColor;
        this._edgeColor =
            styles.getPropertyValue("--inom-rule").trim() || this._edgeColor;
        this._faintColor =
            styles.getPropertyValue("--inom-ink-faint").trim() || this._faintColor;
    }

    async _loadInterval() {
        // Read once at mount, not per poll -- an ir.config_parameter lookup
        // on every tick is a pointless DB hit.
        try {
            const value = await this.orm.call(
                "ir.config_parameter", "get_param",
                ["inom_server_health.poll_interval_s", "10"]
            );
            const seconds = parseInt(value, 10);
            if (!Number.isNaN(seconds)) {
                this.state.intervalMs =
                    Math.max(seconds * 1000, MIN_INTERVAL_MS);
            }
        } catch {
            // Keep the default. Not worth surfacing.
        }
    }

    _restoreLocal() {
        // A page refresh should not throw away the fine-grained trace the user
        // was watching. Cron history is one point per minute; this is the
        // detail between those points.
        try {
            const raw = browser.sessionStorage.getItem(STORAGE_KEY);
            if (!raw) {
                return;
            }
            const stored = JSON.parse(raw);
            const floor = Date.now() - WINDOW_MS;
            for (const channel of this.channels) {
                this.points[channel.key] = (stored[channel.key] || [])
                    .filter((p) => p && p.t >= floor);
            }
        } catch {
            // Corrupt or unavailable storage is not worth surfacing.
        }
    }

    _persistLocal() {
        try {
            browser.sessionStorage.setItem(
                STORAGE_KEY, JSON.stringify(this.points));
        } catch {
            // Quota or private mode. The trace still works in-session.
        }
    }

    async _loadSeed() {
        // Opens the trace mid-flight from cron-captured history rather than an
        // empty canvas. Merged by timestamp with anything restored locally, so
        // a refresh keeps detail while still filling gaps from the server.
        try {
            const response = await browser.fetch("/inom_server_health/seed", {
                method: "GET", headers: { Accept: "application/json" },
            });
            if (!response.ok) {
                return;
            }
            const payload = await response.json();
            const known = new Set(
                (this.points.cpu || []).map((p) => p.t));
            for (const point of payload.points || []) {
                if (known.has(point.t)) {
                    continue;
                }
                this._push({
                    cpu: point.cpu,
                    mem: point.mem,
                    db: point.db,
                    load: this._loadPercent(point.load_raw, 1),
                }, point.t);
            }
            for (const channel of this.channels) {
                this.points[channel.key].sort((a, b) => a.t - b.t);
            }
        } catch {
            // History is a nicety. A cold instance simply starts empty.
        }
    }

    // ----- polling -------------------------------------------------------

    _clearTimer() {
        if (this._timer) {
            browser.clearTimeout(this._timer);
            this._timer = null;
        }
    }

    _schedule(delayMs) {
        if (this._stopped || this.state.paused || this.state.manualPause) {
            return;
        }
        this._clearTimer();
        this._timer = browser.setTimeout(() => this._tick(), delayMs);
    }

    async _tick() {
        if (this._stopped) {
            return;
        }
        try {
            const response = await browser.fetch("/inom_server_health/live", {
                method: "GET", headers: { Accept: "application/json" },
            });
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            const payload = await response.json();
            this.state.data = this.state.demo
                ? this._applyDemoSpike(payload)
                : payload;
            this.state.error = null;
            this._failures = 0;

            const cores = payload.host
                && payload.host.cpu_allowance
                && payload.host.cpu_allowance[0];
            this._push({
                cpu: payload.host && payload.host.cpu_percent,
                mem: payload.host && payload.host.memory
                    && payload.host.memory.percent,
                db: payload.postgres && payload.postgres.conn_percent,
                load: this._loadPercent(
                    payload.host && payload.host.load
                        && payload.host.load["1m"],
                    cores),
            });
            this._draw();
            this._persistLocal();
            this._schedule(this.state.intervalMs);
        } catch (error) {
            this._failures += 1;
            this.state.error = error.message || _t("Cannot reach the server");
            const backoff = Math.min(
                this.state.intervalMs * Math.pow(2, this._failures),
                MAX_BACKOFF_MS
            );
            this._schedule(backoff);
        } finally {
            this.state.loading = false;
        }
    }

    /**
     * Demo mode. Fabricates a load spike on top of the real payload so the
     * warning and danger states can be seen without waiting for a real
     * incident -- for screenshots and store listings.
     *
     * Reachable only via ?health_demo=1, never on by default, and the UI
     * carries a banner the whole time it is active. Fabricated numbers that
     * look real are the single worst thing a monitoring tool can do, so this
     * is kept loud and opt-in.
     */
    _applyDemoSpike(payload) {
        if (!this._spikeUntil || Date.now() > this._spikeUntil) {
            return payload;
        }
        const jitter = (base) => Math.min(
            99, base + (Math.random() - 0.5) * 6);
        const fake = JSON.parse(JSON.stringify(payload));
        fake.host.cpu_percent = jitter(93);
        if (fake.host.memory) {
            fake.host.memory.percent = jitter(94);
        }
        fake.postgres.conn_percent = jitter(88);
        fake.postgres.conn_total = Math.round(
            (fake.postgres.conn_max || 100) * 0.88);
        fake.postgres.cache_hit_pct = 94.2;
        fake.postgres.longest_query_s = 412;
        fake.postgres.longest_idle_tx_s = 190;
        fake.odoo.mail = { outgoing: 1284, failed: 17 };
        fake.odoo.crons = {
            active_count: fake.odoo.crons?.active_count || 0,
            late_count: 3,
            late: [
                { id: 1, name: "Mail: Email Queue Manager", behind_s: 620 },
                { id: 2, name: "Base: Auto-vacuum internal data", behind_s: 1980 },
                { id: 3, name: "Sales: Send invoice reminders", behind_s: 240 },
            ],
        };
        return fake;
    }

    triggerDemoSpike() {
        this._spikeUntil = Date.now() + 60000;
        this._tick();
    }

    togglePause() {
        this.state.manualPause = !this.state.manualPause;
        if (!this.state.manualPause) {
            this._tick();
        } else {
            this._clearTimer();
        }
    }

    refreshNow() {
        this._tick();
    }

    clearTrace() {
        for (const channel of this.channels) {
            this.points[channel.key] = [];
        }
        try {
            browser.sessionStorage.removeItem(STORAGE_KEY);
        } catch {
            // Nothing to do.
        }
        this._draw();
    }

    /** Load average is absolute; the trace is a percentage plot. */
    _loadPercent(raw, cores) {
        const value = parseFloat(raw);
        if (Number.isNaN(value)) {
            return null;
        }
        return Math.min(100, (value / (cores || 1)) * 100);
    }

    _push(sample, timestamp) {
        const t = timestamp || Date.now();
        const floor = t - WINDOW_MS;
        for (const channel of this.channels) {
            const buffer = this.points[channel.key];
            const incoming = sample[channel.key];
            // A null -- e.g. the first CPU delta in a fresh worker -- carries
            // the previous value forward rather than punching a hole.
            const value = (incoming === null || incoming === undefined)
                ? (buffer.length ? buffer[buffer.length - 1].v : null)
                : incoming;
            if (value === null || value === undefined) {
                continue;
            }
            buffer.push({ t, v: value });

            // Prune by age first, then by count. Age is what the axis means;
            // the count cap only guards against an unbounded tab.
            let cut = 0;
            while (cut < buffer.length && buffer[cut].t < floor) {
                cut += 1;
            }
            if (cut) {
                buffer.splice(0, cut);
            }
            if (buffer.length > MAX_POINTS) {
                buffer.splice(0, buffer.length - MAX_POINTS);
            }
            this.state.latest[channel.key] = value;
        }
    }

    // ----- the trace -----------------------------------------------------

    _resize() {
        const canvas = this.canvasRef.el;
        if (!canvas) {
            return;
        }
        const ratio = browser.devicePixelRatio || 1;
        const box = canvas.getBoundingClientRect();
        canvas.width = Math.max(1, Math.round(box.width * ratio));
        canvas.height = Math.max(1, Math.round(box.height * ratio));
        canvas.getContext("2d").setTransform(ratio, 0, 0, ratio, 0, 0);
    }

    _draw() {
        const canvas = this.canvasRef.el;
        if (!canvas) {
            return;
        }
        const ctx = canvas.getContext("2d");
        const box = canvas.getBoundingClientRect();
        const width = box.width;
        const height = box.height;
        const gutter = 52;
        const plotWidth = Math.max(10, width - gutter);

        ctx.clearRect(0, 0, width, height);

        // Reference grid. Hairlines only -- the traces are the content.
        ctx.lineWidth = 1;
        ctx.strokeStyle = this._gridColor;
        ctx.fillStyle = this._faintColor;
        ctx.font = "10px ui-monospace, SFMono-Regular, Menlo, monospace";
        for (const level of [0, 25, 50, 75, 100]) {
            const y = Math.round(height - (level / 100) * height) + 0.5;
            ctx.beginPath();
            ctx.moveTo(0, y);
            ctx.lineTo(plotWidth, y);
            ctx.stroke();
            if (level && level < 100) {
                ctx.fillText(`${level}%`, plotWidth + 6, y + 3);
            }
        }

        // Position by timestamp, so coarse history and fine live data sit
        // where they actually belong on the axis.
        const now = Date.now();
        const xAt = (t) => plotWidth * (1 - (now - t) / WINDOW_MS);
        const yAt = (v) => height - (v / 100) * height;

        for (const channel of this.channels) {
            if (!channel.on) {
                continue;
            }
            const data = this.points[channel.key]
                .filter((p) => p.t >= now - WINDOW_MS);
            if (data.length < 2) {
                continue;
            }

            // Filled area first, faint -- density without shouting.
            ctx.beginPath();
            ctx.moveTo(xAt(data[0].t), height);
            data.forEach((p) => ctx.lineTo(xAt(p.t), yAt(p.v)));
            ctx.lineTo(xAt(data[data.length - 1].t), height);
            ctx.closePath();
            ctx.globalAlpha = 0.08;
            ctx.fillStyle = channel.color;
            ctx.fill();
            ctx.globalAlpha = 1;

            ctx.beginPath();
            data.forEach((p, i) => (i
                ? ctx.lineTo(xAt(p.t), yAt(p.v))
                : ctx.moveTo(xAt(p.t), yAt(p.v))));
            ctx.strokeStyle = channel.color;
            ctx.lineWidth = 1.75;
            ctx.lineJoin = "round";
            ctx.stroke();

            // Leading dot at the "now" edge -- the recorder's pen.
            const lastX = xAt(data[data.length - 1].t);
            const lastY = yAt(data[data.length - 1].v);
            ctx.beginPath();
            ctx.arc(lastX, lastY, 3, 0, Math.PI * 2);
            ctx.fillStyle = channel.color;
            ctx.fill();
            ctx.globalAlpha = 0.28;
            ctx.beginPath();
            ctx.arc(lastX, lastY, 6, 0, Math.PI * 2);
            ctx.strokeStyle = channel.color;
            ctx.lineWidth = 1;
            ctx.stroke();
            ctx.globalAlpha = 1;
        }

        // Time gridlines every 15 minutes, labelled, so the axis is readable
        // rather than implied.
        ctx.strokeStyle = this._gridColor;
        ctx.fillStyle = this._faintColor;
        for (let back = 15; back < WINDOW_MS / 60000; back += 15) {
            const x = Math.round(xAt(now - back * 60000)) + 0.5;
            if (x < 2) {
                continue;
            }
            ctx.beginPath();
            ctx.moveTo(x, 0);
            ctx.lineTo(x, height - 12);
            ctx.stroke();
            ctx.fillText(`-${back}m`, x + 4, height - 3);
        }

        ctx.beginPath();
        ctx.moveTo(Math.round(plotWidth) + 0.5, 0);
        ctx.lineTo(Math.round(plotWidth) + 0.5, height);
        ctx.strokeStyle = this._edgeColor;
        ctx.lineWidth = 1;
        ctx.stroke();
    }

    toggleChannel(key) {
        const channel = this.channels.find((c) => c.key === key);
        if (!channel) {
            return;
        }
        channel.on = !channel.on;
        this.state.channelsOn[key] = channel.on;
        this._draw();
    }

    channelColor(key) {
        const channel = this.channels.find((c) => c.key === key);
        return channel ? channel.color : "transparent";
    }

    get windowLabel() {
        const minutes = Math.round(WINDOW_MS / 60000);
        return minutes >= 90
            ? _t("last %s hours", (minutes / 60).toFixed(1))
            : _t("last %s minutes", minutes);
    }

    // ----- formatting ----------------------------------------------------

    bytes(value) {
        if (value === null || value === undefined) {
            return "—";
        }
        const units = ["B", "KB", "MB", "GB", "TB"];
        let index = 0;
        let number = value;
        while (number >= 1024 && index < units.length - 1) {
            number /= 1024;
            index += 1;
        }
        return `${number.toFixed(number < 10 && index > 0 ? 1 : 0)} ${units[index]}`;
    }

    pct(value) {
        return (value === null || value === undefined)
            ? "—" : Number(value).toFixed(1);
    }

    duration(seconds) {
        if (!seconds) {
            return "—";
        }
        const days = Math.floor(seconds / 86400);
        const hours = Math.floor((seconds % 86400) / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        if (days) {
            return `${days}d ${hours}h`;
        }
        if (hours) {
            return `${hours}h ${minutes}m`;
        }
        return `${minutes}m`;
    }

    /** Thresholds in one place so the colour language stays consistent. */
    severity(value, warn, danger) {
        if (value === null || value === undefined) {
            return "";
        }
        if (value >= danger) {
            return "danger";
        }
        if (value >= warn) {
            return "warning";
        }
        return "";
    }

    barWidth(value) {
        const number = Number(value);
        return Number.isNaN(number)
            ? "0%" : `${Math.min(100, Math.max(0, number))}%`;
    }

    // ----- derived views over the payload --------------------------------

    get host() {
        return (this.state.data && this.state.data.host) || {};
    }

    get memory() {
        return this.host.memory || {};
    }

    get pg() {
        return (this.state.data && this.state.data.postgres) || {};
    }

    get odoo() {
        return (this.state.data && this.state.data.odoo) || {};
    }

    get crons() {
        return this.odoo.crons || {};
    }

    get mail() {
        return this.odoo.mail || {};
    }

    get users() {
        return this.odoo.users || {};
    }

    get activeUsers() {
        return this.users.users || [];
    }

    get workers() {
        return (this.odoo.workers && this.odoo.workers.items) || [];
    }

    get workersAvailable() {
        return !!(this.odoo.workers && this.odoo.workers.available);
    }

    get disks() {
        return this.host.disks || [];
    }

    get capabilities() {
        return (this.state.data && this.state.data.capabilities) || {};
    }

    get coreLabel() {
        const allowance = this.host.cpu_allowance;
        if (!allowance) {
            return "";
        }
        return allowance[2]
            ? _t("%s of %s cores (capped)", allowance[0], allowance[1])
            : _t("%s cores", allowance[0]);
    }

    /** Alerts assembled as sentences, most severe first. */
    get alerts() {
        const out = [];
        if (!this.state.data) {
            return out;
        }
        if (this.mail.failed) {
            out.push({
                id: "mail-failed", sev: "danger", who: _t("Mail"),
                text: _t("%s message(s) failed to send, %s still queued.",
                    this.mail.failed, this.mail.outgoing || 0),
            });
        }
        if (this.crons.late_count) {
            const names = (this.crons.late || []).slice(0, 3)
                .map((c) => `${c.name} (${this.duration(c.behind_s)} late)`)
                .join(" · ");
            out.push({
                id: "cron-late", sev: "warning", who: _t("Crons"),
                text: _t("%s scheduled action(s) behind schedule — %s",
                    this.crons.late_count, names),
            });
        }
        if ((this.pg.longest_idle_tx_s || 0) > 60) {
            out.push({
                id: "idle-tx", sev: "warning", who: _t("Postgres"),
                text: _t("A transaction has been idle for %s. Idle "
                    + "transactions hold locks and block VACUUM.",
                    this.duration(this.pg.longest_idle_tx_s)),
            });
        }
        if (this.capabilities.pg_monitor === false) {
            out.push({
                id: "pg-monitor", sev: "", who: _t("Setup"),
                text: _t("Only Odoo's own database sessions are visible. "
                    + "Grant the pg_monitor role to the database user for "
                    + "the full picture."),
            });
        }
        return out;
    }
}

registry.category("actions").add(
    "inom_server_health.dashboard", ServerHealthDashboard);
