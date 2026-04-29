/** @odoo-module **/

import { Component, useRef, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class ReplyBox extends Component {

    static template = "chatter_reply_system.ReplyBox";

    static props = {
        // Parent message info
        messageId   : { type: Number },
        authorName  : { type: String },
        quotedBody  : { type: String },
        replyType   : { type: String },   // 'comment' ya 'note'
        resModel    : { type: String },
        resId       : { type: Number },

        // Callbacks
        onClose     : { type: Function },
        onReplySent : { type: Function },
    };

    setup() {
        this.rpc         = useService("rpc");
        this.notification = useService("notification");
        this.replyTextarea = useRef("replyTextarea");

        this.state = useState({
            body     : "",
            sending  : false,
        });
    }

    // ── Input change track karo ───────────────────────
    onInput(ev) {
        this.state.body = ev.target.value;
    }

    // ── SEND button click (Message) ───────────────────
    async onSend() {
        if (!this.state.body.trim()) {
            this.notification.add("Reply cannot be empty!", { type: "warning" });
            return;
        }
        await this._postReply("comment");
    }

    // ── LOG button click (Log Note) ───────────────────
    async onLog() {
        if (!this.state.body.trim()) {
            this.notification.add("Reply cannot be empty!", { type: "warning" });
            return;
        }
        await this._postReply("note");
    }

    // ── Discard button click ──────────────────────────
    onDiscard() {
        this.state.body = "";
        this.props.onClose();
    }

    // ── Reply post karo (common method) ──────────────
    async _postReply(replyType) {
        this.state.sending = true;

        try {
            // Python method call karo
            await this.rpc("/web/dataset/call_kw", {
                model  : "mail.message.reply",
                method : "action_send_reply",
                args   : [
                    [],
                    this.props.messageId,
                    this._buildBody(),        // quoted + reply body
                    replyType,
                ],
                kwargs : {},
            });

            // Success notification
            this.notification.add(
                replyType === "comment"
                    ? "Reply sent successfully!"
                    : "Log note added successfully!",
                { type: "success" }
            );

            // Parent ko notify karo — chatter refresh hoga
            this.props.onReplySent();
            this.props.onClose();

        } catch (error) {
            this.notification.add(
                "Failed to send reply. Please try again.",
                { type: "danger" }
            );
            console.error("Reply error:", error);

        } finally {
            this.state.sending = false;
        }
    }

    // ── Final body banana: quoted + user reply ────────
    _buildBody() {
        const quoted = `
            <blockquote style="
                border-left : 4px solid #adb5bd;
                padding     : 6px 12px;
                margin      : 6px 0;
                color       : #555;
                background  : #f8f9fa;
            ">
                ${this.props.quotedBody}
            </blockquote>
        `;

        const userReply = `<p>${this.state.body}</p>`;

        return quoted + userReply;
    }
}