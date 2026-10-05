import { registry } from "@web/core/registry";

// Chatter: Reply icon must be directly visible on hover (not hidden in "Expand")
function clickReplyOn(text) {
    return [
        {
            trigger: `.o-mail-Chatter .o-mail-Message:contains('${text}')`,
            run: "hover",
        },
        {
            trigger: `.o-mail-Chatter .o-mail-Message:contains('${text}') .o-mail-Message-actions button[name='reply-to'][title='Reply']:visible`,
            run: "click",
        },
    ];
}

// Discuss: Reply lives in the message "Expand" (more actions) dropdown
function clickExpandReplyOn(text, container) {
    return [
        {
            trigger: `${container} .o-mail-Message:contains('${text}')`,
            run: `hover && click .o-mail-Message:contains('${text}') [title='Expand']`,
        },
        {
            trigger: ".o-dropdown-item[name='reply-to']",
            run: "click",
        },
    ];
}

// Reply on a log note → custom log-note dialog → posted as a note
registry.category("web_tour.tours").add("inom_chatter_reply_log_note_tour", {
    steps: () => [
        ...clickReplyOn("Original internal note"),
        {
            trigger: ".o_log_reply_body",
        },
        {
            // Quoted original message and author are shown
            trigger: "blockquote:contains('Original internal note')",
        },
        {
            // Empty body is rejected
            trigger: ".o_log_reply_submit",
            run: "click",
        },
        {
            trigger: ".o_log_reply_error:visible",
        },
        {
            trigger: ".o_log_reply_body",
            run: "edit Reply <b>not bold</b>",
        },
        {
            trigger: ".o_log_reply_submit",
            run: "click",
        },
        {
            trigger: "body:not(:has(.o_log_reply_body))",
        },
        {
            trigger: ".o-mail-Chatter .o-mail-Message-body:contains('Reply <b>not bold</b>')",
        },
    ],
});

// Discard closes the log-note dialog without posting
registry.category("web_tour.tours").add("inom_chatter_reply_log_note_discard_tour", {
    steps: () => [
        ...clickReplyOn("Original internal note"),
        {
            trigger: ".o_log_reply_body",
            run: "edit Should not be posted",
        },
        {
            trigger: ".o_log_reply_cancel",
            run: "click",
        },
        {
            trigger: "body:not(:has(.o_log_reply_body))",
        },
        ...clickReplyOn("Original internal note"),
        {
            trigger: ".o_log_reply_body",
            run: "press Escape",
        },
        {
            trigger: "body:not(:has(.o_log_reply_body))",
        },
        {
            // Still on the partner form (Escape must not leave the record)
            trigger: ".o_form_view .o-mail-Chatter",
        },
    ],
});

// Reply on a message → mail.compose.message wizard prefilled with quote + author
registry.category("web_tour.tours").add("inom_chatter_reply_comment_tour", {
    steps: () => [
        ...clickReplyOn("Original customer message"),
        {
            trigger: ".modal .o_mail_composer_form_view, .modal .o_form_view",
        },
        {
            trigger: ".modal blockquote:contains('Original customer message')",
        },
        {
            trigger: ".modal div[name='subject'] input:value('Reply Message')",
        },
        {
            trigger: ".modal .o_field_many2many_tags_email .o_tag:contains('Reply Customer')",
        },
        {
            trigger: ".modal button[name='action_send_mail']",
            run: "click",
        },
        {
            trigger: "body:not(:has(.modal))",
        },
        {
            // Chatter refreshed with the new reply on top
            trigger: ".o-mail-Chatter .o-mail-Message:eq(0) .o-mail-Message-header:contains('Administrator')",
        },
    ],
});

// Discuss channels must keep Odoo's native "reply-to" behaviour (no wizard / dialog)
registry.category("web_tour.tours").add("inom_chatter_reply_channel_native_tour", {
    steps: () => [
        ...clickExpandReplyOn("Hello channel", ".o-mail-Discuss"),
        {
            trigger: ".o-mail-Composer:contains('Replying to')",
        },
        {
            trigger: "body:not(:has(.o_log_reply_body)):not(:has(.modal))",
        },
    ],
});
