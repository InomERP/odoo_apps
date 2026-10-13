/** @odoo-module **/

import { Chatter } from "@mail/chatter/web_portal_project/chatter";
import { patch } from "@web/core/utils/patch";

/*
 * Odoo 20 compatibility:
 * The web Chatter component is provided by the chatter/web_portal_project
 * component. Patching the old @mail/core/web/chatter path does not affect
 * the component used by the form chatter, which leaves custom XML handlers
 * undefined at click time.
 */

patch(Chatter.prototype, {
    setup() {
        super.setup(...arguments);
        console.log("[Smart Chatter] Odoo 20 patch loaded");
    },

    _getForm() {
        return document.querySelector(".o_form_view");
    },

    _getChatter() {
        return document.querySelector(".o_ChatterContainer");
    },

    _openPanel() {
        const formView = this._getForm();
        const chatter = this._getChatter();
        if (!formView || !chatter) {
            return;
        }
        chatter.classList.remove("hide", "show");
        void chatter.offsetWidth;
        requestAnimationFrame(() => {
            chatter.classList.add("show");
            formView.classList.add("o_chatter_open");
        });
        document.querySelector(".chatter-close-btn")?.classList.remove("d-none");
        document.querySelector(".o-mail-Chatter-top")?.classList.remove("d-none");
        document.querySelector(".chatter_content")?.classList.remove("d-none");
    },

    _resetView() {
        document
            .querySelectorAll('[aria-label="Message"], [aria-label="Note"], [aria-label="System notification"]')
            .forEach((el) => el.classList.add("d-none"));
        document.querySelector(".o-mail-ActivityList")?.classList.add("d-none");
    },

    _resetActiveIcons() {
        document.querySelectorAll(".o-mail-Form-chatter .icon").forEach((el) => {
            el.classList.remove("active");
        });
    },

    _onClickHeaderMessage() {
        this.toggleComposer("message");
    },

    _onClickHeaderNote() {
        this.toggleComposer("note");
    },

    _onClickSendMessage(ev) {
        this._openPanel();
        this._resetView();
        this._resetActiveIcons();
        ev?.currentTarget?.classList.add("active");
        document.querySelectorAll('[aria-label="Message"]').forEach((el) => {
            el.classList.remove("d-none");
        });
        this.toggleComposer("message");
        document.querySelector("#header_message")?.classList.remove("d-none");
        document.querySelector("#header_note")?.classList.add("d-none");
        this.state?.thread?.update?.({ displayMode: "all" });
    },

    _onClickLogNote(ev) {
        this._openPanel();
        this._resetView();
        this._resetActiveIcons();
        ev?.currentTarget?.classList.add("active");
        document.querySelectorAll('[aria-label="Note"], [aria-label="System notification"]').forEach((el) => {
            el.classList.remove("d-none");
        });
        this.toggleComposer("note");
        document.querySelector("#header_note")?.classList.remove("d-none");
        document.querySelector("#header_message")?.classList.add("d-none");
        this.state?.thread?.update?.({ displayMode: "notes" });
    },

    _onClickActive(ev) {
        this._openPanel();
        this._resetView();
        this._resetActiveIcons();
        ev?.currentTarget?.classList.add("active");
        document.querySelectorAll("[aria-label]").forEach((el) => el.classList.add("d-none"));
        document.querySelector(".o-mail-ActivityList")?.classList.remove("d-none");
        if (typeof this.scheduleActivity === "function") {
            this.scheduleActivity();
        }
        document.querySelector("#header_message")?.classList.add("d-none");
        document.querySelector("#header_note")?.classList.add("d-none");
        this.state?.thread?.update?.({ displayMode: "activities" });
    },

    _onClickCross() {
        const formView = this._getForm();
        const chatter = this._getChatter();
        chatter?.classList.remove("show");
        requestAnimationFrame(() => formView?.classList.remove("o_chatter_open"));
        document.querySelector(".chatter-close-btn")?.classList.add("d-none");
        this._resetView();
        this._resetActiveIcons();
        document.querySelector("#header_message")?.classList.add("d-none");
        document.querySelector("#header_note")?.classList.add("d-none");
        chatter?.classList.add("hide");
    },
});
