/**
 * Odoo 20 visibility-change guard.
 * During a form/action transition, the form root can temporarily exist before
 * activeFields is initialized. Avoid crashing the browser in that transient
 * state; otherwise delegate to the standard Odoo implementation unchanged.
 */
import { patch } from "@web/core/utils/patch";
import { FormController } from "@web/views/form/form_controller";

patch(FormController.prototype, {
    async beforeVisibilityChange(...args) {
        const root = this.model?.root;
        if (!root || !root.activeFields) {
            return;
        }
        return super.beforeVisibilityChange(...args);
    },
});
