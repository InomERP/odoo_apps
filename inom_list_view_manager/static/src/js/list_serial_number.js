/** @odoo-module **/

import { onWillStart, onMounted, onPatched } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";
import { ListRenderer } from "@web/views/list/list_renderer";

patch(ListRenderer.prototype, {

    setup() {
        super.setup(...arguments);

        this.enableSerialNumber = false;

        // CROSS-VERSION NOTE: Odoo 17 does NOT expose a standalone `rpc`
        // function from "@web/core/network/rpc" (it only has the rpc *service*).
        // The `orm` service exists and behaves identically in Odoo 17, 18 and
        // 19, so we use it here to stay compatible across all three.
        this.orm = useService("orm");

        // Loaded BEFORE the first render (onWillStart is awaited by OWL), so the
        // `t-if="this.enableSerialNumber"` guards in the header + row templates
        // have the correct value on the very first paint.
        onWillStart(async () => {
            try {
                this.enableSerialNumber = await this.orm.call(
                    "inom.list.view.manager",
                    "get_serial_number_setting",
                    []
                );
                console.log("Serial Number Setting =", this.enableSerialNumber);
            } catch (error) {
                console.error("Serial Number Setting Error", error);
            }
        });

        // SAFETY NET for the Sr.No HEADER.
        //
        // The header <th> is supposed to come from the OWL template inheritance
        // on `web.ListRenderer` (see list_serial_number.xml). In some Odoo 19
        // builds / asset states that main-template inheritance does NOT take
        // effect (the row inheritance on web.ListRenderer.RecordRow still does),
        // leaving the header missing while the row numbers show. This hook
        // guarantees the header exists by inserting it ONLY when it is absent.
        //
        // It is lifecycle-bound (onMounted/onPatched, no setTimeout), scoped to
        // THIS renderer's table, idempotent (guarded so it never duplicates),
        // and it re-runs after every patch so it survives OWL re-renders caused
        // by drag/drop reorder, hide/show, rename, etc. It is column-agnostic,
        // so it never interferes with the dynamic column features.
        onMounted(() => this._inomEnsureSerialHeader());
        onPatched(() => this._inomEnsureSerialHeader());
    },

    getRowNumber(record) {
        const records = this.props?.list?.records || [];
        const index = records.indexOf(record) + 1;
        return index;
    },

    _inomEnsureSerialHeader() {
        if (!this.enableSerialNumber) return;

        // OWL 2 (Odoo 17+) components have NO `this.el`; the root/table are
        // reached through refs. The core ListRenderer exposes the table via
        // `this.tableRef = useRef("table")`. Using `this.el` (as a previous
        // version did) is always undefined here, which is exactly why the
        // header injection silently did nothing.
        const table = this.tableRef?.el;
        if (!table) return;

        const thead = table.querySelector("thead");
        if (!thead) return;

        // The FIRST <tr> is the real column-header row (the search/filter row,
        // if any, is added AFTER it).
        const headerRow = thead.querySelector("tr");
        if (!headerRow) return;

        // Already present (rendered by the template OR a previous run) -> stop.
        if (headerRow.querySelector(".o_serial_number_header")) return;

        const th = document.createElement("th");
        th.className = "o_serial_number_header text-center";
        th.textContent = "Sr.No";

        // Place it right AFTER the record-selector <th> so it lines up exactly
        // with the row <td> (which is inserted after the selector cell too),
        // making "Sr No" the first data column.
        const selector = headerRow.querySelector("th.o_list_record_selector");
        if (selector) {
            selector.insertAdjacentElement("afterend", th);
        } else {
            // No selector column -> serial becomes the first header cell,
            // matching the row where the serial <td> becomes first too.
            headerRow.prepend(th);
        }
    },
});
