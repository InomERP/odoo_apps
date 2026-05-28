/** @odoo-module **/

/**
 * =====================================================================
 *  VOICE ASSISTANT - COMMAND CONFIGURATION
 * =====================================================================
 *  This is the ONLY file you normally need to edit.
 *
 *  To support a NEW object, add one entry to COMMAND_MAP:
 *      keywords : words a user might SAY for this object (English + Hindi).
 *                 Use lowercase. Hindi can be Devanagari or romanized.
 *      model    : the Odoo technical model name (e.g. "res.partner").
 *      nameField: the field to search the spoken name against.
 *      label    : friendly name shown in notifications.
 *
 *  Recognition language is set in RECOGNITION_LANG below.
 * =====================================================================
 */

// Language used by the browser speech engine.
//   "en-IN" -> Indian English (also catches many common Hindi words)
//   "hi-IN" -> Hindi (Devanagari output)
// You can change this anytime. The parser understands BOTH English and
// Hindi keywords regardless of this setting.
// RECOGNITION_LANG is no longer used — dual recognition (hi-IN + en-IN) is
// handled directly in inom_voice_assistant_service.js
// export const RECOGNITION_LANG = "en-IN";

// Verb synonyms -> intent. Add your own words freely.
export const VERB_MAP = {
    open: ["open", "show", "go to", "खोलो", "खोल", "दिखाओ", "kholo", "dikhao"],
    search: ["search", "find", "list", "खोजो", "ढूंढो", "khojo", "dhundo"],
    create: ["create", "new", "add", "बनाओ", "नया", "banao", "naya"],
};

// keyword -> Odoo model mapping.
// Order matters a little: longer / more specific phrases should come first.
export const COMMAND_MAP = [
    {
        keywords: ["sale order", "sales order", "order", "बिक्री ऑर्डर", "ऑर्डर"],
        model: "sale.order",
        nameField: "name",
        label: "Sales Order",
    },
    {
        keywords: ["purchase order", "purchase", "खरीद", "खरीद ऑर्डर"],
        model: "purchase.order",
        nameField: "name",
        label: "Purchase Order",
    },
    {
        keywords: ["invoice", "bill", "चालान", "बिल", "इनवॉइस"],
        model: "account.move",
        nameField: "name",
        label: "Invoice",
    },
    {
        keywords: ["customer", "contact", "partner", "client", "ग्राहक", "संपर्क", "customer"],
        model: "res.partner",
        nameField: "name",
        label: "Customer",
    },
    {
        keywords: ["product", "item", "उत्पाद", "प्रोडक्ट", "सामान"],
        model: "product.template",
        nameField: "name",
        label: "Product",
    },
    {
        keywords: ["lead", "opportunity", "लीड", "अवसर"],
        model: "crm.lead",
        nameField: "name",
        label: "Lead",
    },
    {
        keywords: ["employee", "कर्मचारी", "employ"],
        model: "hr.employee",
        nameField: "name",
        label: "Employee",
    },
    {
        keywords: ["user", "users", "उपयोगकर्ता", "यूज़र"],
        model: "res.users",
        nameField: "name",
        label: "User",
    },
    {
        keywords: ["company", "companies", "कंपनी"],
        model: "res.company",
        nameField: "name",
        label: "Company",
    },
    {
        keywords: ["project", "परियोजना", "प्रोजेक्ट"],
        model: "project.project",
        nameField: "name",
        label: "Project",
    },
    {
        keywords: ["meeting", "calendar", "मीटिंग", "बैठक"],
        model: "calendar.event",
        nameField: "name",
        label: "Meeting",
    },
    {
        keywords: ["task", "कार्य", "टास्क"],
        model: "project.task",
        nameField: "name",
        label: "Task",
    },
];
