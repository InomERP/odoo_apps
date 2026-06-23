/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";
import { scanBarcode } from "@web/core/barcode/barcode_dialog";
import { isBarcodeScannerSupported } from "@web/core/barcode/barcode_video_scanner";

export class BarcodeScanButton extends Component {
    static template = "inom_multi_user_inventory_count.BarcodeScanButton";
    static props = { ...standardWidgetProps };

    setup() {
        this.notification = useService("notification");
        this.isSupported = isBarcodeScannerSupported();
    }

    async onClickScan() {
        let barcode;
        try {
            barcode = await scanBarcode(this.env);
        } catch {
            this.notification.add(
                _t("Unable to open the camera scanner on this device."),
                { type: "warning" }
            );
            return;
        }
        if (barcode) {
            // Writing the field triggers the server onchange that matches
            // the scanned product.
            await this.props.record.update({ barcode });
        }
    }
}

export const barcodeScanButton = {
    component: BarcodeScanButton,
    fieldDependencies: [{ name: "barcode", type: "char" }],
};

registry.category("view_widgets").add("inom_barcode_scan_button", barcodeScanButton);
