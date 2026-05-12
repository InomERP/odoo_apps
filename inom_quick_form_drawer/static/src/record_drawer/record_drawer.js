/** @odoo-module **/

import { Component, useState, useEffect } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { View } from "@web/views/view";

export class RecordDrawer extends Component {
    static template = "inom_quick_form_drawer.RecordDrawer";
    static components = { View };
    static props = {};

    setup() {
        this.recordDrawer = useService("record_drawer");
        this.state = useState(this.recordDrawer.state);

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