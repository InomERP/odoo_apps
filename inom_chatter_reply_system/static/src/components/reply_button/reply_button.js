/** @odoo-module **/

import { registry } from "@web/core/registry";
import { toRaw } from "@odoo/owl";

const messageActionsRegistry = registry.category("mail.message/actions");


messageActionsRegistry.add("custom_reply", {
    condition: () => true,
    icon: "fa fa-reply",
    name: "Reply",
    sequence: 1,

    onClick: async (component) => {

        const message = toRaw(component.props.message);
        const thread  = toRaw(component.props.thread);

        const resId =
            thread?.res_id ||
            thread?.id;

        const resModel =
            thread?.model;

        if (!resId || !resModel) {
            return;
        }

        //------------------------------------------------------------------
        // ✅ Detect Log Note
        //------------------------------------------------------------------
        const isLogNote =
        message.subtype_id?.xml_id === "mail.mt_note" ||
        message.is_note === true ||
        (message.message_type === "comment" && !message.partner_ids?.length);

        //------------------------------------------------------------------
        // Quote
        //------------------------------------------------------------------
        const author = message.author?.name || "Unknown";
        const body   = message.body || "";

        const date = message.date
            ? new Date(message.date).toLocaleString()
            : "";

        const quotedBody = `
            <p>On ${date}, <strong>${author}</strong> wrote:</p>
            <blockquote style="border-left:4px solid #adb5bd;padding:6px 12px;margin:6px 0;color:#555;background:#f8f9fa;">
                ${body}
            </blockquote>
            <p><br/></p>
        `;

        const authorPartnerId = message.author?.id || false;
        const partnerIds = authorPartnerId ? [authorPartnerId] : [];

        //------------------------------------------------------------------
        // Context
        //------------------------------------------------------------------
        const context = isLogNote
            ? {
                default_model: resModel,
                default_res_ids: [resId],
                default_parent_id: message.id,
                default_body: quotedBody,

                // 📝 Log Note
                default_is_log: true,
                default_subtype_xmlid: "mail.mt_note",
                default_partner_ids: [],
                default_message_type: "comment",
                mail_post_autofollow: false,
            }
            : {
                default_model: resModel,
                default_res_ids: [resId],
                default_parent_id: message.id,
                default_body: quotedBody,
                default_subject: "Reply Message",

                // 📧 Mail
                default_is_log: false,
                default_subtype_xmlid: "mail.mt_comment",
                default_partner_ids: partnerIds,
                default_composition_mode: "comment",
            };

        //------------------------------------------------------------------
        // Action
        //------------------------------------------------------------------
        const actionService = component.env.services.action;

        await actionService.doAction({
            type: "ir.actions.act_window",
            res_model: "mail.compose.message",
            views: [[false, "form"]],
            target: "new",
            context: context,
        });

    },
});