/** @odoo-module **/

import { Chatter } from "@mail/chatter/web_portal/chatter";
import { patch } from "@web/core/utils/patch";
import { useRef } from "@odoo/owl";
patch(Chatter.prototype, {
    setup(...args) {
        super.setup(...args);
        this.root = useRef("main_root");
    },
    _openPanel() {
        const root = this.root.el;
        const chatter = root.querySelector('.o_ChatterContainer');
        const formView = root.closest('.o_form_view');
        if (!chatter) return
        chatter.classList.remove("hide", "show");
        void chatter.offsetWidth;
        requestAnimationFrame(() => {
            chatter.classList.add("show");
            formView?.classList.add('o_chatter_open');
        });
        root.querySelector('.chatter-close-btn')?.classList.remove("d-none");
        root.querySelector('.o-mail-Chatter-top')?.classList.remove("d-none");
        root.querySelector('.chatter_content')?.classList.remove("d-none");
    },
    _resetView() {
        const root = this.root.el;

        root.querySelectorAll('[aria-label="Message"], [aria-label="Note"], [aria-label="System notification"]')
            .forEach(el => el.classList.add('d-none'));
        root.querySelector('.o-mail-ActivityList')?.classList.add("d-none");
    },
    _resetActiveIcons() {
        this.root.el.querySelectorAll('.icon').forEach(el => {
            el.classList.remove('active');
        });
    },
    _onClickSendMessage(ev) {
        this._openPanel();
        this._resetView();
        this._resetActiveIcons();
        ev.currentTarget.classList.add("active");
        this.root.el.querySelectorAll('[aria-label="Message"]').forEach(el => {
            el.classList.remove('d-none');
        });
        this.toggleComposer('message');
        this.root.el.querySelector('#header_message')?.classList.remove("d-none");
        this.root.el.querySelector('#header_note')?.classList.add("d-none");
        this.state.thread.update({ displayMode: 'all' });
    },
    _onClickLogNote(ev) {
        this._openPanel();
        this._resetView();
        this._resetActiveIcons();
        ev.currentTarget.classList.add("active");
        this.root.el.querySelectorAll('[aria-label="Note"], [aria-label="System notification"]').forEach(el => {
            el.classList.remove('d-none');
        });
        this.toggleComposer('note');
        this.root.el.querySelector('#header_note')?.classList.remove("d-none");
        this.root.el.querySelector('#header_message')?.classList.add("d-none");
        this.state.thread.update({ displayMode: 'notes' });
    },
    _onClickActive(ev) {
        this._openPanel();
        this._resetView();
        this._resetActiveIcons();
        ev.currentTarget.classList.add("active");
        this.root.el.querySelectorAll('[aria-label="Message"], [aria-label="Note"], [aria-label="System notification"]')
            .forEach(el => el.classList.add('d-none'));
        this.root.el.querySelector('.o-mail-ActivityList')?.classList.remove("d-none");
        this.scheduleActivity();
        this.root.el.querySelector('#header_message')?.classList.add("d-none");
        this.root.el.querySelector('#header_note')?.classList.add("d-none");

        this.state.thread.update({ displayMode: 'activities' });
    },
    _onClickCross() {
        const root = this.root.el;
        const formView = root.closest('.o_form_view');
        const chatter = root.querySelector('.o_ChatterContainer');
        chatter?.classList.remove("show");
        requestAnimationFrame(() => {
            formView?.classList.remove('o_chatter_open');
        });
        root.querySelector('.chatter-close-btn')?.classList.add("d-none");
        this._resetView();
        this._resetActiveIcons();
        root.querySelector('#header_message')?.classList.add("d-none");
        root.querySelector('#header_note')?.classList.add("d-none");
        chatter?.classList.add("hide");
    }
});