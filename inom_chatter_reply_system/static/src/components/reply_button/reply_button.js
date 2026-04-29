/** @odoo-module **/

import { registry } from "@web/core/registry";
import { toRaw } from "@odoo/owl";

const messageActionsRegistry = registry.category("mail.message/actions");
const existingReplyTo = messageActionsRegistry.get("reply-to");

if (existingReplyTo) {

    console.log("🚀 [ReplyPatch] Loaded");

    existingReplyTo.condition = (component) => {
        const thread = component.props.thread;

        const result = thread?.model !== "mail.box";

        return result;
    };

    existingReplyTo.onClick = async (component) => {


        const message = toRaw(component.props.message);
        const thread  = toRaw(component.props.thread);


        const resId    = thread?.res_id || thread?.id || false;
        const resModel = thread?.model  || false;

        if (!resId || !resModel) {
            return;
        }

        //------------------------------------------------------------------
        // 🔍 FIX 1: LOG NOTE DETECTION
        //------------------------------------------------------------------
       const subtype = message.subtype_description || "";
        const subtypeXml = message.subtype_xmlid || "";

       const isLogNote =
            message.is_note === true ||
            message.subtype_description === "Note";
        //------------------------------------------------------------------
        // ✉️ Quote Builder
        //------------------------------------------------------------------
        const author = message.author?.name || "Unknown";
        const body   = message.body         || "";
        const date   = message.date
            ? message.date.toFormat("yyyy-MM-dd HH:mm:ss")
            : "";

        const quotedBody = `
            <p>On ${date}, <strong>${author}</strong> wrote:</p>
            <blockquote style="
                border-left  : 4px solid #adb5bd;
                padding      : 6px 12px;
                margin       : 6px 0;
                color        : #555;
                background   : #f8f9fa;
                border-radius: 2px;
            ">${body}</blockquote>
            <p><br/></p>
        `;

        //------------------------------------------------------------------
        // 👥 Partner logic
        //------------------------------------------------------------------
        const authorPartnerId = message.author?.id || false;
        const partnerIds      = authorPartnerId ? [authorPartnerId] : [];

        //------------------------------------------------------------------
        // 🔥 CONTEXT BUILD
        //------------------------------------------------------------------
        let context;

        if (isLogNote) {

            context = {
                default_model: resModel,
                default_res_ids: [resId],
                default_parent_id: message.id,
                default_body: quotedBody,

                default_is_log: true,
                default_subtype_xmlid: "mail.mt_note",
                default_composition_mode: "comment",


                // 🔥 CRITICAL
                default_partner_ids: [],
                default_email_to: false,
                default_email_cc: false,

                default_message_type: "comment",
                mail_post_autofollow: false,
            };

        } else {

            context = {
                default_model: resModel,
                default_res_ids: [resId],
                default_parent_id: message.id,
                default_body: quotedBody,
                default_subject: "Reply Message",

                default_is_log: false,
                default_subtype_xmlid: "mail.mt_comment",
                default_partner_ids: partnerIds,
                default_composition_mode: "comment",
            };
        }

        console.log("📦 FINAL CONTEXT:", context);

        //------------------------------------------------------------------
        // 🚀 ACTION CALL
        //------------------------------------------------------------------
        const actionService = component.env.services.action;

        await actionService.doAction({
            type      : "ir.actions.act_window",
            res_model : "mail.compose.message",
            views     : [[false, "form"]],
            target    : "new",
            context   : context,
        });

        console.log("✅ Action triggered");
    };
}