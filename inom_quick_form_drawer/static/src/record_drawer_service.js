/** @odoo-module **/

import { registry } from "@web/core/registry";
import { reactive } from "@odoo/owl";

/**
 * Global service that holds the state of the record drawer.
 *
 * Usage from any component:
 *      this.env.services.record_drawer.open(resModel, resId);
 *      this.env.services.record_drawer.close();
 *
 * The `RecordDrawer` main component listens to the reactive `state` and
 * shows / hides itself accordingly.
 */
export const recordDrawerService = {
    start() {
        const state = reactive({
            isOpen: false,
            resModel: null,
            resId: null,
            instanceKey: 0,
        });

        return {
            state,

            open(resModel, resId) {
                if (!resModel || !resId) {
                    return;
                }
                state.resModel = resModel;
                state.resId = resId;
                state.instanceKey += 1;
                state.isOpen = true;
            },

            close() {
                state.isOpen = false;
                setTimeout(() => {
                    if (!state.isOpen) {
                        state.resModel = null;
                        state.resId = null;
                    }
                }, 300);
            },

            toggle(resModel, resId) {
                if (state.isOpen && state.resModel === resModel && state.resId === resId) {
                    this.close();
                } else {
                    this.open(resModel, resId);
                }
            },
        };
    },
};

registry.category("services").add("record_drawer", recordDrawerService);
