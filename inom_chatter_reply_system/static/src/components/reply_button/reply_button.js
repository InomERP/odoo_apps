/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { Message } from "@mail/core/common/message";
import { IS_ACTION_DEFINITION_SYM } from "@mail/core/common/action";
import { messageActionsRegistry } from "@mail/core/common/message_actions";

const escape = (str) =>
    String(str ?? "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#x27;");

// Odoo 20: action definitions must carry IS_ACTION_DEFINITION_SYM, otherwise
// useMessageActions() filters them out. We wrap the native "reply-to" action so that
// Discuss channels keep the native behaviour and only chatter messages use our flow.
const nativeReplyTo = messageActionsRegistry.get("reply-to", null);

function isChatterReply({ channel, message, owner }) {
    return Boolean(
        !channel &&
            owner.env.inChatter &&
            !owner.env.inMessagingMenu &&
            !message.isEmpty &&
            (message.isNote || message.isDiscussion)
    );
}

messageActionsRegistry.add("reply-to", {
    ...(nativeReplyTo || {}),
    condition: (params) =>
        isChatterReply(params) || Boolean(nativeReplyTo?.condition?.(params)),
    icon: "reply",
    name: nativeReplyTo?.name || "Reply",
    onSelected: (params) => {
        if (isChatterReply(params) && typeof params.owner.onToggleReplyMenu === "function") {
            return params.owner.onToggleReplyMenu(params);
        }
        return nativeReplyTo?.onSelected?.(params);
    },
    // In chatter, show Reply right after the reaction button (inline on hover)
    sequence: (params) => {
        if (isChatterReply(params)) {
            return 15;
        }
        const nativeSequence = nativeReplyTo?.sequence;
        return typeof nativeSequence === "function" ? nativeSequence(params) : nativeSequence ?? 20;
    },
    [IS_ACTION_DEFINITION_SYM]: true,
}, { force: true });

// Patch Message component
patch(Message.prototype, {

    // Odoo 20 shows only 1 quick action + "Expand" on hover: keep one more slot
    // in chatter so the Reply icon is directly visible instead of hidden in "Expand".
    get quickActionCount() {
        const count = super.quickActionCount;
        if (
            this.env.inChatter &&
            count > 1 &&
            this.messageActions.actions.some((action) => action.id === "reply-to")
        ) {
            return count + 1;
        }
        return count;
    },

    onToggleReplyMenu(params = {}) {
        const isLogNote = this.props.message.isNote || false;
        return this.onClickReply(isLogNote ? "note" : "comment", params.thread);
    },

    async onClickReply(replyType, thread) {
        const message  = this.props.message;
        const resModel = message.model  || message.thread?.model || thread?.model;
        const resId    = message.res_id || message.thread?.id    || thread?.id;

        if (!resId || !resModel) {
            console.error("[Reply] resId/resModel not found:", message);
            return;
        }

        if (replyType === "note") {
            await this._openLogNoteDialog(message, resId, resModel);
        } else {
            await this._openCommentWizard(message, resId, resModel);
        }
    },

    _refreshReplyThread(message) {
        const thread = message.thread || this.props.thread;
        if (thread && typeof thread.fetchNewMessages === "function") {
            thread.fetchNewMessages();
        }
    },

    // ── LOG NOTE: Custom dialog + direct orm.call ─────────────────────
    async _openLogNoteDialog(message, resId, resModel) {
        const quotedBody = this._buildQuotedBody(message);

        // Build overlay
        const overlay = document.createElement("div");
        overlay.style.cssText = `
            position : fixed;
            inset    : 0;
            background: rgba(0,0,0,.45);
            display  : flex;
            align-items: center;
            justify-content: center;
            z-index  : 9999;
        `;

        overlay.innerHTML = `
            <div style="
                background   : #fff;
                border-radius: 8px;
                width        : 620px;
                max-width    : 95vw;
                max-height   : 90vh;
                overflow-y   : auto;
                padding      : 24px;
                font-family  : inherit;
                box-shadow   : 0 8px 32px rgba(0,0,0,.2);
            ">
                <h5 style="margin:0 0 14px; font-size:16px; font-weight:600; color:#333;">
                    Add Log Note (Reply)
                </h5>

                <!-- Quoted original message -->
                <div style="
                    border       : 1px solid #dee2e6;
                    border-radius: 4px;
                    padding      : 10px 14px;
                    margin-bottom: 12px;
                    font-size    : 13px;
                    color        : #555;
                    background   : #f8f9fa;
                ">
                    ${quotedBody}
                </div>

                <!-- User types here -->
                <textarea class="o_log_reply_body" placeholder="Write your log note here..." style="
                    width        : 100%;
                    min-height   : 110px;
                    border       : 1px solid #dee2e6;
                    border-radius: 4px;
                    padding      : 8px 10px;
                    font-size    : 14px;
                    box-sizing   : border-box;
                    resize       : vertical;
                    outline      : none;
                    font-family  : inherit;
                    transition   : border-color .15s;
                "></textarea>
                <p class="o_log_reply_error" style="
                    color    : #dc3545;
                    font-size: 12px;
                    margin   : 4px 0 0;
                    display  : none;
                ">Message body is required.</p>

                <!-- Buttons -->
                <div style="margin-top:14px; display:flex; gap:8px; align-items:center;">
                    <button type="button" class="o_log_reply_submit" style="
                        background   : #714b67;
                        color        : #fff;
                        border       : none;
                        padding      : 8px 22px;
                        border-radius: 4px;
                        cursor       : pointer;
                        font-size    : 14px;
                        font-weight  : 500;
                    ">Log</button>
                    <button type="button" class="o_log_reply_cancel" style="
                        background   : #fff;
                        color        : #333;
                        border       : 1px solid #dee2e6;
                        padding      : 8px 22px;
                        border-radius: 4px;
                        cursor       : pointer;
                        font-size    : 14px;
                    ">Discard</button>
                    <span class="o_log_reply_spinner" style="
                        display  : none;
                        font-size: 13px;
                        color    : #888;
                    ">Sending...</span>
                </div>
            </div>
        `;

        const textarea  = overlay.querySelector(".o_log_reply_body");
        const errMsg    = overlay.querySelector(".o_log_reply_error");
        const spinner   = overlay.querySelector(".o_log_reply_spinner");
        const submitBtn = overlay.querySelector(".o_log_reply_submit");

        const close = () => {
            document.removeEventListener("keydown", onKeydown, true);
            overlay.remove();
        };
        // Escape closes the dialog; stop it so Odoo doesn't also close the form view
        const onKeydown = (e) => {
            if (e.key === "Escape") {
                e.stopPropagation();
                close();
            }
        };
        document.addEventListener("keydown", onKeydown, true);
        document.body.appendChild(overlay);

        // Auto-focus textarea
        setTimeout(() => textarea.focus(), 50);

        // Close on backdrop click
        overlay.addEventListener("click", (e) => {
            if (e.target === overlay) close();
        });

        // Discard button
        overlay.querySelector(".o_log_reply_cancel").onclick = close;

        // Submit button
        submitBtn.onclick = async () => {
            const body = textarea.value.trim();

            // Validate
            if (!body) {
                textarea.style.borderColor = "#dc3545";
                errMsg.style.display = "block";
                return;
            }
            textarea.style.borderColor = "#dee2e6";
            errMsg.style.display = "none";

            // Loading state
            submitBtn.disabled      = true;
            submitBtn.style.opacity = "0.7";
            spinner.style.display   = "inline";

            // User text is plain text: escape it before turning it into HTML
            const fullBody = `${quotedBody}<p>${escape(body).replace(/\n/g, "<br/>")}</p>`;

            try {
                // Direct ORM call — no wizard, no validation issues
                await this.env.services.orm.call(resModel, "post_log_reply", [[resId]], {
                    body      : fullBody,
                    parent_id : message.id,
                });

                close();
                this._refreshReplyThread(message);

            } catch (err) {
                console.error("[LogNote] Error:", err);
                this.env.services.notification.add(
                    "Failed to add log note. Please try again.",
                    { type: "danger" }
                );
                submitBtn.disabled      = false;
                submitBtn.style.opacity = "1";
                spinner.style.display   = "none";
            }
        };
    },

    // ── COMMENT: mail.compose.message wizard ─────────────────────────
    async _openCommentWizard(message, resId, resModel) {
        const quotedBody = this._buildQuotedBody(message);
        // author_id is a res.partner; guests (author_guest_id) cannot be recipients
        const authorPartnerId = message.author_id?.id;
        const partnerIds      = authorPartnerId ? [authorPartnerId] : [];

        await this.env.services.action.doAction(
            {
                type      : "ir.actions.act_window",
                res_model : "mail.compose.message",
                view_mode : "form",
                views     : [[false, "form"]],
                target    : "new",
                context   : {
                    default_model            : resModel,
                    default_res_ids          : [resId],
                    default_parent_id        : message.id,
                    default_body             : `${quotedBody}<p><br/></p>`,
                    default_subject          : "Reply Message",
                    default_composition_mode : "comment",
                    default_message_type     : "comment",
                    default_subtype_xmlid    : "mail.mt_comment",
                    default_partner_ids      : partnerIds,
                    inom_chatter_reply       : true,
                },
            },
            {
                onClose: () => this._refreshReplyThread(message),
            }
        );
    },

    // ── Build quoted block ────────────────────────────────────────────
    _buildQuotedBody(message) {
        const author = escape(message.author?.name || "Unknown");
        // message.body is server-sanitized HTML (Markup)
        const body   = message.body || "";
        // datetime is in the user's timezone (date is UTC)
        const date   = message.datetime
            ? escape(message.datetime.toFormat("yyyy-MM-dd HH:mm:ss"))
            : "";
        return `<p style="margin:0 0 4px;font-size:13px;">On ${date}, <strong>${author}</strong> wrote:</p>` +
               `<blockquote style="border-left:4px solid #adb5bd;padding:6px 12px;margin:4px 0 0;color:#555;background:#f8f9fa;border-radius:2px;font-size:13px;">${body}</blockquote>`;
    },

});
