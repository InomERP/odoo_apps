/** @odoo-module **/

import { Component, useEffect } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { View } from "@web/views/view";

export class RecordDrawer extends Component {
    static template = "inom_quick_form_drawer.RecordDrawer";
    static components = { View };

    setup() {
        this.recordDrawer = useService("record_drawer");
        // The service state is already an OWL 3 reactive proxy.
        // Keep the same proxy instead of wrapping it again with useState.
        this.state = this.recordDrawer.state;

        useEffect(() => {
            const onKeydown = (ev) => {
                if (ev.key === "Escape" && this.state.isOpen) {
                    this.onClose();
                }
            };
            document.addEventListener("keydown", onKeydown);
            return () => document.removeEventListener("keydown", onKeydown);
        }, () => [this.state.isOpen]);
    }

    get viewProps() {
        return {
            type: "form",
            resModel: this.state.resModel,
            resId: this.state.resId,
            display: {
                controlPanel: { layoutActions: false },
            },
        };
    }

    onClose() {
        this.recordDrawer.close();
    }

    onBackdropClick() {
        this.onClose();
    }
}

registry.category("main_components").add("inom_quick_form_drawer.RecordDrawer", {
    Component: RecordDrawer,
});