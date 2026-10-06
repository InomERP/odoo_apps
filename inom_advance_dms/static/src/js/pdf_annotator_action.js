/** @odoo-module **/

import { Component, onMounted, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { openAnnotator } from "./pdf_annotator";

/**
 * PdfAnnotateButton – a client action that is invoked via the form's
 * "Annotate PDF" button (name="action_open_pdf_annotator", type="object").
 *
 * We also inject the button directly into the form header via a small
 * monkey-patch on the form controller event so it works without changing views.
 */

// ---------------------------------------------------------------------------
//  Direct "Annotate PDF" action called from Python action_open_pdf_annotator
// ---------------------------------------------------------------------------
async function openAnnotatorFromRecord(env, action) {
    const { context } = action;
    const fileName = context.file_name;
    const documentId = context.document_id;

    if (!fileName) {
        env.services.notification.add("No PDF file found for annotation.", { type: "warning" });
        return;
    }

    // Preferred path: stream the binary from the dedicated route rather than
    // carrying a base64 copy of the whole file inside the action context.
    if (context.file_url) {
        try {
            const response = await fetch(context.file_url);
            if (!response.ok) {
                throw new Error("HTTP " + response.status);
            }
            const buffer = await response.arrayBuffer();
            await openAnnotator(documentId, new Uint8Array(buffer), fileName);
            return;
        } catch (error) {
            console.error("Could not stream the PDF:", error);
            env.services.notification.add("Could not load the PDF file.", { type: "danger" });
            return;
        }
    }

    // Legacy fallback: a base64 payload in the context.
    if (!context.file_data) {
        env.services.notification.add("No PDF file found for annotation.", { type: "warning" });
        return;
    }

    await openAnnotator(documentId, context.file_data, fileName);
}

registry.category("actions").add("edm_open_pdf_annotator", openAnnotatorFromRecord);
