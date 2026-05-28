/** @odoo-module **/

import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { reactive } from "@odoo/owl";
import { parseCommand } from "./command_parser";
import { COMMAND_MAP as STATIC_COMMAND_MAP } from "./command_config";

/**
 * voiceAssistantService
 * ---------------------
 * Dual-language recognition: runs TWO SpeechRecognition instances in parallel
 * — one for Hindi (hi-IN) and one for Indian English (en-IN).
 * Whichever produces a parseable command first wins. This ensures both
 * "open customer Sachin" and "ग्राहक सचिन खोलो" work without any setting change.
 *
 * state.status: "idle" | "listening" | "recognized" | "processing" | "success" | "error"
 */
export const voiceAssistantService = {
    dependencies: ["orm", "action"],

    start(env, { orm, action }) {
        const SpeechRecognition =
            window.SpeechRecognition || window.webkitSpeechRecognition;

        const state = reactive({
            supported: Boolean(SpeechRecognition),
            status: "idle",
            text: "",
            visible: false,
        });

        // Two recognition instances: Hindi + English
        let recHindi = null;
        let recEnglish = null;
        let hideTimer = null;

        // Guard: once one instance fires a final result, ignore the other.
        let commandHandled = false;

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

        function stopBoth() {
            try { recHindi && recHindi.stop(); } catch (e) {}
            try { recEnglish && recEnglish.stop(); } catch (e) {}
        }

        function makeRecognition(lang) {
            if (!SpeechRecognition) return null;
            const rec = new SpeechRecognition();
            rec.lang = lang;
            rec.continuous = false;
            rec.interimResults = true;
            rec.maxAlternatives = 4;

            rec.onresult = (event) => {
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
                    // If the other language already handled this utterance, skip.
                    if (commandHandled) return;

                    const alternatives = [];
                    for (let i = event.resultIndex; i < event.results.length; i++) {
                        if (event.results[i].isFinal) {
                            for (let a = 0; a < event.results[i].length; a++) {
                                alternatives.push(event.results[i][a].transcript.trim());
                            }
                        }
                    }
                    show("recognized", `"${finalText}"`);
                    commandHandled = true;
                    stopBoth();
                    handleCommand(finalText, alternatives);
                } else if (interim && state.status === "listening") {
                    show("listening", interim);
                }
            };

            rec.onerror = (event) => {
                // "aborted" fires when we manually stop() — not a real error.
                if (event.error === "aborted") return;
                // Only show error if BOTH instances fail (other may still succeed).
                if (state.status !== "processing" && state.status !== "recognized") {
                    if (event.error === "not-allowed" || event.error === "service-not-allowed") {
                        show("error", _t("Microphone blocked — allow it in the browser."), 5000);
                    } else if (event.error === "network") {
                        show("error", _t("No connection to speech service — check internet."), 5000);
                    } else if (event.error === "no-speech") {
                        show("error", _t("Didn't catch that — tap mic to retry."), 3000);
                    }
                }
            };

            rec.onend = () => {
                if (state.status === "listening" && !commandHandled) {
                    // This instance ended with no result; wait for the other one.
                    // If both end with no result, the hide() in stop() covers it.
                }
            };

            return rec;
        }

        if (SpeechRecognition) {
            recHindi   = makeRecognition("hi-IN");
            recEnglish = makeRecognition("en-IN");
        }

        function start() {
            if (!state.supported) {
                show("error", _t("Voice not supported — use Chrome or Edge."), 5000);
                return;
            }
            if (state.status === "listening") return;

            commandHandled = false;
            show("listening", _t("Listening… (English या Hindi)"));
            try { recHindi.start(); }   catch (e) {}
            try { recEnglish.start(); } catch (e) {}
        }

        function stop() {
            stopBoth();
            hide();
        }

        function toggle() {
            state.status === "listening" ? stop() : start();
        }

        async function loadCommandMap() {
            let dynamic = [];
            try {
                dynamic = await orm.call("voice.command", "get_commands", []);
            } catch (e) {
                dynamic = [];
            }
            dynamic = (dynamic || []).filter(
                (c) =>
                    c.keywords &&
                    c.keywords.length &&
                    ((c.kind === "object" && c.model) ||
                        (c.kind === "action" && c.actionId))
            );
            return [...dynamic, ...STATIC_COMMAND_MAP];
        }

        async function nameSearch(model, query, limit = 20) {
            try {
                const res = await orm.call(model, "name_search", [], {
                    name: query || "",
                    operator: "ilike",
                    limit,
                });
                return (res || []).map(([id, name]) => ({ id, name: name || "" }));
            } catch (e) {
                return null;
            }
        }

        function pickBest(records, query) {
            if (records.length === 1) return { record: records[0] };
            const q = (query || "").toLowerCase().trim();
            if (q) {
                const exact = records.filter((r) => r.name.toLowerCase() === q);
                if (exact.length === 1) return { record: exact[0] };
                const starts = records.filter((r) => r.name.toLowerCase().startsWith(q));
                if (starts.length === 1) return { record: starts[0] };
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
                domain: [["id", "in", ids]],
                views: [[false, "list"], [false, "form"]],
                target: "current",
            });
            show("success", _t("Found %s %s — pick one.", ids.length, label), 2500);
        }

        async function handleCommand(text, alternatives = [text]) {
            const commandMap = await loadCommandMap();

            let cmd = null;
            for (const phrase of alternatives) {
                const parsed = parseCommand(phrase, commandMap);
                if (parsed) { cmd = parsed; break; }
            }
            if (!cmd) {
                show("error", _t('Did not understand: "%s"', text), 4000);
                return;
            }

            show("processing", _t("Working on it…"));

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

            let records = await nameSearch(cmd.model, cmd.query);
            if (records === null) {
                show("error", _t("Could not search %s (access?).", cmd.label), 4000);
                return;
            }

            if (records.length === 0 && cmd.query) {
                const words = cmd.query.split(/\s+/).filter((w) => w.length > 2);
                for (const w of words) {
                    const r = await nameSearch(cmd.model, w);
                    if (r && r.length) { records = r; break; }
                }
            }

            if (!records || records.length === 0) {
                show("error", _t('No %s found for "%s".', cmd.label, cmd.query), 4000);
                return;
            }

            if (cmd.intent === "search") {
                openList(cmd.model, records.map((r) => r.id), cmd.label, cmd.query);
                return;
            }

            const best = pickBest(records, cmd.query);
            if (best.record) {
                openForm(cmd.model, best.record.id, cmd.label, best.record.name);
            } else {
                openList(cmd.model, records.map((r) => r.id), cmd.label, cmd.query);
            }
        }

        window.addEventListener("keydown", (ev) => {
            if (ev.ctrlKey && ev.code === "Space" && !ev.repeat) {
                ev.preventDefault();
                toggle();
            }
        });

        setTimeout(() => {
            if (state.supported) {
                show("ready", _t("Voice ready — Ctrl+Space (English & हिंदी)"), 4000);
            } else {
                show("error", _t("Voice not supported — use Chrome or Edge."), 5000);
            }
        }, 1200);

        return { state, toggle, start, stop, hide };
    },
};

registry.category("services").add("inom_voice_assistant", voiceAssistantService);
