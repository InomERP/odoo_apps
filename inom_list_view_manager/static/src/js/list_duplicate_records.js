/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { onMounted, onPatched } from "@odoo/owl";
import { ListController } from "@web/views/list/list_controller";
import { useService } from "@web/core/utils/hooks";

patch(ListController.prototype, {
    setup() {
        // FIX: super.setup() → super.setup(...arguments) for correct OWL behaviour
        super.setup(...arguments);
        this.orm = useService("orm");
        this.notification = useService("notification");
        onMounted(() => { this._showDuplicateButton(); });
        onPatched(() => { this._showDuplicateButton(); });
    },

    _showDuplicateButton() {
        const btn = document.querySelector(".o_duplicate_records_btn");
        if (!btn) return;
        const isListView = !!document.querySelector(".o_list_renderer");
        if (isListView) {
            btn.style.display = "inline-flex";
            if (!btn.dataset.bound) {
                btn.dataset.bound = "1";
                btn.addEventListener("click", () => {
                    this.duplicateSelectedRecords();
                });
            }
        } else {
            btn.style.display = "none";
        }
    },

    async duplicateSelectedRecords() {
        const selected = this.model.root.records.filter((rec) => rec.selected);
        if (!selected.length) {
            this.notification.add("Please select records first!", { type: "warning" });
            return;
        }
        try {
            for (const rec of selected) {
                await this.orm.call(this.props.resModel, "copy", [rec.resId]);
            }
            this.notification.add(
                `${selected.length} record(s) duplicated successfully!`,
                { type: "success" }
            );
            await this.model.load();
            this.render(true);
        } catch (error) {
            console.error("Duplicate error:", error);
            this.notification.add("Duplication failed. Please try again.", { type: "danger" });
        }
    },
});