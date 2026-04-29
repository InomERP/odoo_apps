/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { Message } from "@mail/core/common/message";
import { messageActionsRegistry } from "@mail/core/common/message_actions";
import { Action } from "@mail/core/common/action";
import { useService } from "@web/core/utils/hooks";

// Remove default reply actions
["reply-to", "reply"].forEach((key) => {
    try { messageActionsRegistry.remove(key); } catch (_) {}
});

// Add custom reply action
messageActionsRegistry.add("reply-to", {
    condition: (component) => component.message.thread?.model !== "mail.box",
    icon:      "fa fa-reply",
    name:      "Reply",
    sequence:  55,
});

// Patch Action to handle reply-to click
patch(Action.prototype, {
    onSelected(ev) {
        if (this.id !== "reply-to") return super.onSelected(...arguments);
        const owner = this.owner;
        if (owner && typeof owner.onToggleReplyMenu === "function") {
            owner.onToggleReplyMenu(ev);
        }
    },
});

// Patch Message component
patch(Message.prototype, {

    setup() {
        super.setup(...arguments);
        this.actionService = useService("action");
        this.orm           = useService("orm");
        this.notification  = useService("notification");
    },

    onToggleReplyMenu(ev) {
        const isLogNote = this.props.message.isNote || false;
        isLogNote ? this.onClickReply("note") : this.onClickReply("comment");
    },

    async onClickReply(replyType) {
        const message  = this.props.message;
        const resId    = message.res_id    || message.thread?.res_id;
        const resModel = message.model     || message.thread?.model || false;

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
                <textarea id="log-reply-body" placeholder="Write your log note here..." style="
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
                <p id="log-reply-error" style="
                    color    : #dc3545;
                    font-size: 12px;
                    margin   : 4px 0 0;
                    display  : none;
                ">Message body is required.</p>

                <!-- Buttons -->
                <div style="margin-top:14px; display:flex; gap:8px; align-items:center;">
                    <button id="log-reply-submit" style="
                        background   : #714b67;
                        color        : #fff;
                        border       : none;
                        padding      : 8px 22px;
                        border-radius: 4px;
                        cursor       : pointer;
                        font-size    : 14px;
                        font-weight  : 500;
                    ">Log</button>
                    <button id="log-reply-cancel" style="
                        background   : #fff;
                        color        : #333;
                        border       : 1px solid #dee2e6;
                        padding      : 8px 22px;
                        border-radius: 4px;
                        cursor       : pointer;
                        font-size    : 14px;
                    ">Discard</button>
                    <span id="log-reply-spinner" style="
                        display  : none;
                        font-size: 13px;
                        color    : #888;
                    ">Sending...</span>
                </div>
            </div>
        `;

        document.body.appendChild(overlay);

        // Auto-focus textarea
        setTimeout(() => overlay.querySelector("#log-reply-body").focus(), 50);

        // Close on backdrop click
        overlay.addEventListener("click", (e) => {
            if (e.target === overlay) overlay.remove();
        });

        // Discard button
        overlay.querySelector("#log-reply-cancel").onclick = () => overlay.remove();

        // Submit button
        overlay.querySelector("#log-reply-submit").onclick = async () => {
            const textarea = overlay.querySelector("#log-reply-body");
            const errMsg   = overlay.querySelector("#log-reply-error");
            const spinner  = overlay.querySelector("#log-reply-spinner");
            const submitBtn = overlay.querySelector("#log-reply-submit");
            const body     = textarea.value.trim();

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

            const fullBody = `
                ${quotedBody}
                <p>${body.replace(/\n/g, "<br/>")}</p>
            `;

            try {
                // Direct ORM call — no wizard, no validation issues
            await this.orm.call(resModel, "post_log_reply", [[resId]], {
                res_id    : resId,
                body      : fullBody,
                parent_id : message.id,
            });

                overlay.remove();

                // Refresh chatter
                const thread = message.thread;
                if (thread && typeof thread.fetchNewMessages === "function") {
                    thread.fetchNewMessages();
                }

            } catch (err) {
                console.error("[LogNote] Error:", err);
                this.notification.add("Failed to add log note. Please try again.", { type: "danger" });
                submitBtn.disabled      = false;
                submitBtn.style.opacity = "1";
                spinner.style.display   = "none";
            }
        };
    },

    // ── COMMENT: mail.compose.message wizard (works fine) ────────────
    async _openCommentWizard(message, resId, resModel) {
        const quotedBody      = this._buildQuotedBody(message);
        const authorPartnerId = message.author?.id || false;
        const partnerIds      = authorPartnerId ? [authorPartnerId] : [];

        await this.actionService.doAction({
            type      : "ir.actions.act_window",
            res_model : "mail.compose.message",
            views     : [[false, "form"]],
            target    : "new",
            context   : {
                default_model            : resModel,
                default_res_ids          : [resId],
                default_parent_id        : message.id,
                default_body             : quotedBody || "<p><br/></p>",
                default_subject          : "Reply Message",
                default_composition_mode : "comment",
                default_message_type     : "comment",
                default_is_log           : false,
                default_subtype_xmlid    : "mail.mt_comment",
                default_partner_ids      : [[6, 0, partnerIds]],
                active_model             : resModel,
                active_ids               : [resId],
            },
        });
    },

    // ── Build quoted block ────────────────────────────────────────────
   _buildQuotedBody(message) {
    const author = message.author?.name || "Unknown";
    const body   = message.body         || "";
    const date   = message.date
                   ? message.date.toFormat("yyyy-MM-dd HH:mm:ss")
                   : "";
    return `<p style="margin:0 0 4px;font-size:13px;">On ${date}, <strong>${author}</strong> wrote:</p>` +
           `<blockquote style="border-left:4px solid #adb5bd;padding:6px 12px;margin:4px 0 0;color:#555;background:#f8f9fa;border-radius:2px;font-size:13px;">${body}</blockquote>`;
},

});