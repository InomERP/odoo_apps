/** @odoo-module **/

import { Chatter } from "@mail/core/web/chatter";
import { patch } from "@web/core/utils/patch";

patch(Chatter.prototype, {

    setup() {
        super.setup();
        console.log("✅ PATCH APPLIED");
    },

    // ✅ ALWAYS GET CORRECT FORM ROOT
    _getForm() {
        return document.querySelector('.o_form_view');
    },

    // ✅ GET CHATTER PANEL DIRECTLY
    _getChatter() {
        return document.querySelector('.o_ChatterContainer');
    },

    // ================= OPEN PANEL =================
    _openPanel() {
        const formView = this._getForm();
        const chatter = this._getChatter();

        if (!formView || !chatter) {
            console.log("❌ Form or Chatter not found");
            return;
        }

        chatter.classList.remove("hide", "show");
        void chatter.offsetWidth;

        requestAnimationFrame(() => {
            chatter.classList.add("show");
            formView.classList.add('o_chatter_open');
        });

        document.querySelector('.chatter-close-btn')?.classList.remove("d-none");
        document.querySelector('.o-mail-Chatter-top')?.classList.remove("d-none");
        document.querySelector('.chatter_content')?.classList.remove("d-none");
    },

    // ================= RESET =================
    _resetView() {
        document.querySelectorAll('[aria-label="Message"], [aria-label="Note"], [aria-label="System notification"]')
            .forEach(el => el.classList.add('d-none'));

        document.querySelector('.o-mail-ActivityList')?.classList.add("d-none");
    },

    _resetActiveIcons() {
        document.querySelectorAll('.icon').forEach(el => {
            el.classList.remove('active');
        });
    },

    // ================= HEADER =================
    _onClickHeaderMessage() {
        console.log("🔥 HEADER MESSAGE");
        this.toggleComposer('message');
    },

    _onClickHeaderNote() {
        console.log("🔥 HEADER NOTE");
        this.toggleComposer('note');
    },

    // ================= MAIN BUTTONS =================
    _onClickSendMessage(ev) {
        console.log("🔥 SEND CLICKED");

        this._openPanel();
        this._resetView();
        this._resetActiveIcons();

        ev?.currentTarget?.classList.add("active");

        document.querySelectorAll('[aria-label="Message"]').forEach(el => {
            el.classList.remove('d-none');
        });

        this.toggleComposer('message');

        document.querySelector('#header_message')?.classList.remove("d-none");
        document.querySelector('#header_note')?.classList.add("d-none");

        this.state.thread?.update({ displayMode: 'all' });
    },

    _onClickLogNote(ev) {
        console.log("🔥 NOTE CLICKED");

        this._openPanel();
        this._resetView();
        this._resetActiveIcons();

        ev?.currentTarget?.classList.add("active");

        document.querySelectorAll('[aria-label="Note"], [aria-label="System notification"]').forEach(el => {
            el.classList.remove('d-none');
        });

        this.toggleComposer('note');

        document.querySelector('#header_note')?.classList.remove("d-none");
        document.querySelector('#header_message')?.classList.add("d-none");

        this.state.thread?.update({ displayMode: 'notes' });
    },

    _onClickActive(ev) {
        console.log("🔥 ACTIVITY CLICKED");

        this._openPanel();
        this._resetView();
        this._resetActiveIcons();

        ev?.currentTarget?.classList.add("active");

        document.querySelectorAll('[aria-label]').forEach(el => {
            el.classList.add('d-none');
        });

        document.querySelector('.o-mail-ActivityList')?.classList.remove("d-none");

        this.scheduleActivity();

        document.querySelector('#header_message')?.classList.add("d-none");
        document.querySelector('#header_note')?.classList.add("d-none");

        this.state.thread?.update({ displayMode: 'activities' });
    },

    // ================= CLOSE =================
    _onClickCross() {
        console.log("🔥 CLOSE CLICKED");

        const formView = this._getForm();
        const chatter = this._getChatter();

        chatter?.classList.remove("show");

        requestAnimationFrame(() => {
            formView?.classList.remove('o_chatter_open');
        });

        document.querySelector('.chatter-close-btn')?.classList.add("d-none");

        this._resetView();
        this._resetActiveIcons();

        document.querySelector('#header_message')?.classList.add("d-none");
        document.querySelector('#header_note')?.classList.add("d-none");

        chatter?.classList.add("hide");
    }
});