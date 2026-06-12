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
    const fileData = context.file_data;
    const fileName = context.file_name;
    const documentId = context.document_id;

    if (!fileData || !fileName) {
        env.services.notification.add("No PDF file found for annotation.", { type: "warning" });
        return;
    }

    await openAnnotator(documentId, fileData, fileName);
}

registry.category("actions").add("edm_open_pdf_annotator", openAnnotatorFromRecord);
