/** @odoo-module **/

import { VERB_MAP } from "./command_config";

/**
 * Parse a recognized speech string into a structured command.
 *
 * @param {string} rawText    e.g. "open customer Sachin"
 * @param {Array}  commandMap list of { keywords[], label, kind, model,
 *                            actionId, nameField } -- merged DB + static.
 * @returns {Object|null}
 *   object cmd : { intent, model, nameField, label, query }
 *   action cmd : { intent: "action", actionId, label }
 */
export function parseCommand(rawText, commandMap) {
    if (!rawText) {
        return null;
    }
    const text = rawText.toLowerCase().trim();

    // 1) Detect the intent (verb). Default to "open".
    let intent = "open";
    let matchedVerb = "";
    for (const [name, words] of Object.entries(VERB_MAP)) {
        for (const w of words) {
            if (text.includes(w) && w.length > matchedVerb.length) {
                intent = name;
                matchedVerb = w;
            }
        }
    }

    // 2) Detect the object/action by keyword (longest match wins).
    let target = null;
    let matchedKeyword = "";
    for (const entry of commandMap) {
        for (const kw of entry.keywords) {
            if (kw && text.includes(kw) && kw.length > matchedKeyword.length) {
                target = entry;
                matchedKeyword = kw;
            }
        }
    }

    if (!target) {
        return null;
    }

    // 3a) "Open action" commands just launch the action -- verb/name ignored.
    if (target.kind === "action") {
        return {
            intent: "action",
            actionId: target.actionId,
            label: target.label,
        };
    }

    // 3b) "Open model" commands: extract the name query.
    let query = text;
    if (matchedVerb) {
        query = query.replace(matchedVerb, " ");
    }
    query = query.replace(matchedKeyword, " ");
    // Normalise spoken separators and stray punctuation.
    query = query
        .replace(/\b(slash|स्लैश)\b/g, "/")
        .replace(/\b(dash|hyphen|डैश)\b/g, "-")
        .replace(/[.,!?;:"']/g, " ");
    // Strip filler words (greetings, politeness, articles).
    query = query
        .replace(/\b(hi|hey|hello|ok|okay|yo|namaste|नमस्ते|kindly|just|can you|could you|would you)\b/g, " ")
        .replace(/\b(the|a|an|named|name|number|no|for|please|to|me|ka|ki|ke|को|का|की|वाला)\b/g, " ")
        .replace(/\s+/g, " ")
        .trim();

    return {
        intent,
        model: target.model,
        nameField: target.nameField || "name",
        label: target.label,
        query,
    };
}
