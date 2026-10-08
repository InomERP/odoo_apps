/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { MailComposerFormController } from "@mail/chatter/web/mail_composer_form";

/**
 * Odoo 20's generic FormController can receive a visibility-change event while
 * the mail composer model is being torn down/rebuilt. In that short window the
 * root record may not have activeFields yet. The core implementation assumes
 * activeFields is always present and crashes with:
 * "Cannot read properties of undefined (reading 'activeFields')".
 *
 * The mail composer is a dialog and does not need the visibility-change save
 * operation while its form model is not initialized. Guard that transient
 * state, then delegate to Odoo's normal implementation once activeFields is
 * available.
 */
patch(MailComposerFormController.prototype, {
    async beforeVisibilityChange() {
        if (!this.model?.root?.activeFields) {
            return;
        }
        return super.beforeVisibilityChange(...arguments);
    },
});
