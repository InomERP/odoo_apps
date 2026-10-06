/** @odoo-module **/

import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { proxy } from "@odoo/owl";
import { parseCommand } from "./command_parser";
import { RECOGNITION_LANG, COMMAND_MAP as STATIC_COMMAND_MAP } from "./command_config";

/**
 * voiceAssistantService
 * ---------------------
 * Owns the browser SpeechRecognition object, the global Ctrl+Space hotkey,
 * and the logic that turns a parsed command into an Odoo action.
 *
 * Exposes a reactive `state` consumed by the bottom-center overlay
 * (inom_voice_assistant_overlay.js). The overlay shows a single Siri-style pill
 * that updates in place -- no stacked notifications.
 *
 * state.status is one of:
 *   "idle" | "listening" | "recognized" | "processing" | "success" | "error"
 */
export const voiceAssistantService = {
    dependencies: ["orm", "action"],

    start(env, { orm, action }) {
        const SpeechRecognition =
            window.SpeechRecognition || window.webkitSpeechRecognition;

        const state = proxy({
            supported: Boolean(SpeechRecognition),
            status: "idle",
            text: "",        // recognized speech or status message
            visible: false,  // is the overlay pill shown?
            level: 0,        // live mic input level 0-100 while listening
        });

        // Live mic level meter (runs alongside SpeechRecognition) so the user
        // can SEE whether the browser is actually receiving their voice.
        let meter = null;
        let peakLevel = 0;
        async function startMeter() {
            stopMeter();
            peakLevel = 0;
            try {
                const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                const ctx = new (window.AudioContext || window.webkitAudioContext)();
                const analyser = ctx.createAnalyser();
                analyser.fftSize = 1024;
                ctx.createMediaStreamSource(stream).connect(analyser);
                const buf = new Float32Array(analyser.fftSize);
                const startedAt = performance.now();
                const timer = setInterval(() => {
                    analyser.getFloatTimeDomainData(buf);
                    let sum = 0;
                    for (const v of buf) {
                        sum += v * v;
                    }
                    // RMS -> rough 0-100 scale (normal speech lands ~30-80).
                    const level = Math.min(100, Math.round(Math.sqrt(sum / buf.length) * 400));
                    state.level = level;
                    // Ignore the first ~600ms: many laptop mics emit a loud
                    // "pop" when capture starts, which is not speech.
                    if (performance.now() - startedAt > 600) {
                        peakLevel = Math.max(peakLevel, level);
                    }
                }, 80);
                meter = { stream, ctx, timer };
            } catch {
                meter = null;
            }
        }
        function stopMeter() {
            if (meter) {
                clearInterval(meter.timer);
                meter.stream.getTracks().forEach((t) => t.stop());
                meter.ctx.close();
                meter = null;
            }
            state.level = 0;
        }

        let recognition = null;
        let hideTimer = null;

        // Show the pill with a status; optionally auto-hide after `ms`.
        function show(status, text, ms = 0) {
            clearTimeout(hideTimer);
            state.status = status;
            state.text = text;
            state.visible = true;
            if (ms > 0) {
                hideTimer = setTimeout(() => hide(), ms);
            }
        }
        function hide() {
            clearTimeout(hideTimer);
            state.visible = false;
            state.status = "idle";
            state.text = "";
        }

        if (state.supported) {
            recognition = new SpeechRecognition();
            recognition.lang = RECOGNITION_LANG;
            recognition.continuous = false;
            recognition.interimResults = true;
            recognition.maxAlternatives = 4;

            recognition.onresult = (event) => {
                // Build the interim (still-being-spoken) and final transcripts.
                let interim = "";
                let finalText = "";
                for (let i = event.resultIndex; i < event.results.length; i++) {
                    const chunk = event.results[i][0].transcript;
                    if (event.results[i].isFinal) {
                        finalText += chunk;
                    } else {
                        interim += chunk;
                    }
                }
                finalText = finalText.trim();
                interim = interim.trim();

                if (finalText) {
                    // Collect ALL recognition alternatives for the final phrase.
                    // The top guess sometimes misses a keyword the 2nd guess has,
                    // so we let the parser try each until one matches.
                    const alternatives = [];
                    for (let i = event.resultIndex; i < event.results.length; i++) {
                        if (event.results[i].isFinal) {
                            for (let a = 0; a < event.results[i].length; a++) {
                                alternatives.push(event.results[i][a].transcript.trim());
                            }
                        }
                    }
                    show("recognized", `"${finalText}"`);
                    handleCommand(finalText, alternatives);
                } else if (interim) {
                    // Live caption while the user is still talking. Keep the
                    // waveform (status stays "listening") and show the words.
                    show("listening", interim);
                }
            };

            recognition.onerror = (event) => {
                stopMeter();
                state.status !== "processing" && (state.status = "error");
                if (event.error === "not-allowed") {
                    show("error", _t("Microphone blocked — click the icon left of the URL, allow Microphone, then reload."), 7000);
                } else if (event.error === "service-not-allowed") {
                    // Mic is fine, but the browser refuses the speech service
                    // (e.g. Chromium builds without Google speech, Brave, policy).
                    show("error", _t("Speech service not available in this browser — use Google Chrome or Edge."), 7000);
                } else if (event.error === "audio-capture") {
                    show("error", _t("No microphone found — check your audio input device."), 5000);
                } else if (event.error === "network") {
                    // Web Speech streams audio to the browser vendor's servers.
                    // "network" => that machine can't reach them (offline / proxy / firewall).
                    show("error", _t("No connection to speech service — check internet."), 5000);
                } else if (event.error === "no-speech") {
                    if (peakLevel < 5) {
                        // Browser got (almost) pure silence -> mic/device problem, not speech.
                        show("error", _t("Mic is silent (level %s) — check input device in Chrome/OS sound settings.", peakLevel), 7000);
                    } else {
                        show("error", _t("Didn't catch that (mic level %s) — speak clearly as soon as it says Listening.", peakLevel), 5000);
                    }
                } else if (event.error !== "aborted") {
                    show("error", _t("Voice error: %s", event.error), 4000);
                }
            };

            recognition.onend = () => {
                stopMeter();
                // If we ended while still "listening" (no result, no error), just hide.
                if (state.status === "listening") {
                    hide();
                }
            };
        }

        // Ask for mic access explicitly once. SpeechRecognition alone can fail
        // silently with "not-allowed" without ever showing the browser prompt.
        let micGranted = false;
        async function ensureMicPermission() {
            if (micGranted || !navigator.mediaDevices?.getUserMedia) {
                return true;
            }
            if (!window.isSecureContext) {
                show("error", _t("Microphone needs HTTPS (or localhost)."), 6000);
                return false;
            }
            try {
                const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                stream.getTracks().forEach((t) => t.stop()); // release mic immediately
                micGranted = true;
                return true;
            } catch (e) {
                if (e.name === "NotFoundError") {
                    show("error", _t("No microphone found — check your audio input device."), 5000);
                } else if (e.name === "NotReadableError") {
                    show("error", _t("Microphone is busy in another app — close it and retry."), 5000);
                } else {
                    show("error", _t("Microphone blocked — click the icon left of the URL, allow Microphone, then reload."), 7000);
                }
                return false;
            }
        }

        async function start() {
            if (!state.supported) {
                show("error", _t("Voice not supported — use Chrome or Edge."), 5000);
                return;
            }
            if (state.status === "listening") {
                return; // already listening, ignore
            }
            if (!(await ensureMicPermission())) {
                return;
            }
            try {
                show("listening", _t("Listening…"));
                recognition.start();
                startMeter();
            } catch (e) {
                // start() throws if called while already running; ignore.
            }
        }

        function stop() {
            if (recognition && state.status === "listening") {
                recognition.stop();
            }
            stopMeter();
            hide();
        }

        function toggle() {
            state.status === "listening" ? stop() : start();
        }

        // Load configurable commands from the database (voice.command) and
        // merge them with the built-in static defaults. DB commands take
        // priority (listed first). Re-fetched per command so newly added
        // configuration works without a page reload.
        async function loadCommandMap() {
            let dynamic = [];
            try {
                dynamic = await orm.call("voice.command", "get_commands", []);
            } catch (e) {
                dynamic = []; // model missing / no access -> use static only
            }
            // Keep only usable entries.
            dynamic = (dynamic || []).filter(
                (c) =>
                    c.keywords &&
                    c.keywords.length &&
                    ((c.kind === "object" && c.model) ||
                        (c.kind === "action" && c.actionId))
            );
            return [...dynamic, ...STATIC_COMMAND_MAP];
        }

        // Resolve records using Odoo's own name_search -- the same mechanism
        // its dropdown (Many2one) fields use. Far more accurate than guessing
        // a field, because it respects each model's display-name logic.
        // Returns [{ id, name }, ...].
        async function nameSearch(model, query, limit = 20) {
            try {
                const res = await orm.call(model, "name_search", [], {
                    name: query || "",
                    operator: "ilike",
                    limit,
                });
                return (res || []).map(([id, name]) => ({ id, name: name || "" }));
            } catch (e) {
                return null; // null = error (e.g. access), [] = no matches
            }
        }

        // Pick the best single match for an "open" command.
        // Returns { record } if confident, or { ambiguous: true } if not.
        function pickBest(records, query) {
            if (records.length === 1) {
                return { record: records[0] };
            }
            const q = (query || "").toLowerCase().trim();
            if (q) {
                const exact = records.filter((r) => r.name.toLowerCase() === q);
                if (exact.length === 1) {
                    return { record: exact[0] };
                }
                const starts = records.filter((r) =>
                    r.name.toLowerCase().startsWith(q)
                );
                if (starts.length === 1) {
                    return { record: starts[0] };
                }
            }
            return { ambiguous: true };
        }

        function openForm(model, id, label, name) {
            action.doAction({
                type: "ir.actions.act_window",
                res_model: model,
                res_id: id,
                views: [[false, "form"]],
                target: "current",
            });
            show("success", _t("Opening %s: %s", label, name), 2500);
        }

        function openList(model, ids, label, query) {
            action.doAction({
                type: "ir.actions.act_window",
                name: query ? _t("%s: '%s'", label, query) : label,
                res_model: model,
                // Filter by the exact ids we matched -> always shows the right set.
                domain: [["id", "in", ids]],
                views: [[false, "list"], [false, "form"]],
                target: "current",
            });
            show("success", _t("Found %s %s — pick one.", ids.length, label), 2500);
        }

        async function handleCommand(text, alternatives = [text]) {
            // Load the current command map (DB + static) once per command.
            const commandMap = await loadCommandMap();

            // Try each recognition alternative until one parses to a known command.
            let cmd = null;
            for (const phrase of alternatives) {
                const parsed = parseCommand(phrase, commandMap);
                if (parsed) {
                    cmd = parsed;
                    break;
                }
            }
            if (!cmd) {
                show("error", _t('Did not understand: "%s"', text), 4000);
                return;
            }

            show("processing", _t("Working on it…"));

            // ACTION -> launch a specific configured screen/action by id.
            if (cmd.intent === "action") {
                if (!cmd.actionId) {
                    show("error", _t("No action configured for %s.", cmd.label), 4000);
                    return;
                }
                try {
                    await action.doAction(cmd.actionId);
                    show("success", _t("Opening %s…", cmd.label), 2500);
                } catch (e) {
                    show("error", _t("Could not open %s.", cmd.label), 4000);
                }
                return;
            }

            // CREATE -> open a blank form.
            if (cmd.intent === "create") {
                action.doAction({
                    type: "ir.actions.act_window",
                    name: _t("New %s", cmd.label),
                    res_model: cmd.model,
                    views: [[false, "form"]],
                    target: "current",
                });
                show("success", _t("Opening a new %s…", cmd.label), 2500);
                return;
            }

            // OPEN / SEARCH -> resolve by name_search.
            let records = await nameSearch(cmd.model, cmd.query);
            if (records === null) {
                show("error", _t("Could not search %s (access?).", cmd.label), 4000);
                return;
            }

            // Fallback: if nothing matched the whole phrase, try the individual
            // words (handles extra/reordered words from speech).
            if (records.length === 0 && cmd.query) {
                const words = cmd.query.split(/\s+/).filter((w) => w.length > 2);
                for (const w of words) {
                    const r = await nameSearch(cmd.model, w);
                    if (r && r.length) {
                        records = r;
                        break;
                    }
                }
            }

            if (!records || records.length === 0) {
                show("error", _t('No %s found for "%s".', cmd.label, cmd.query), 4000);
                return;
            }

            // SEARCH intent -> always show the filtered list.
            if (cmd.intent === "search") {
                openList(cmd.model, records.map((r) => r.id), cmd.label, cmd.query);
                return;
            }

            // OPEN intent -> open the best match, or a short list if ambiguous.
            const best = pickBest(records, cmd.query);
            if (best.record) {
                openForm(cmd.model, best.record.id, cmd.label, best.record.name);
            } else {
                openList(cmd.model, records.map((r) => r.id), cmd.label, cmd.query);
            }
        }

        // Global hotkey: Ctrl + Space.
        // `ev.repeat` guard stops the browser's key auto-repeat from firing
        // toggle() dozens of times while the keys are held down.
        window.addEventListener("keydown", (ev) => {
            if (ev.ctrlKey && ev.code === "Space" && !ev.repeat) {
                ev.preventDefault();
                toggle();
            }
        });

        // One-time "ready" confirmation on load. If you SEE this pill, the new
        // assets loaded correctly. Shown shortly after boot, auto-hides in 4s.
        setTimeout(() => {
            if (state.supported) {
                show("ready", _t("Voice assistant ready — press Ctrl+Space"), 4000);
            } else {
                show("error", _t("Voice not supported — use Chrome or Edge."), 5000);
            }
        }, 1200);

        return { state, toggle, start, stop, hide };
    },
};

registry.category("services").add("inom_voice_assistant", voiceAssistantService);
