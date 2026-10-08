/** @odoo-module **/

import { ListController } from "@web/views/list/list_controller";
import { InomDynamicListPanel } from "./dynammic_list";
import { patch } from "@web/core/utils/patch";

// 1. Standard ListController — sirf yahi chahiye
patch(ListController, {
    components: {
        ...ListController.components,
        InomDynamicListPanel,
    },
});

// 2. Purchase - PurchaseFileUploadListController
try {
    const { PurchaseFileUploadListController } = odoo.loader.modules.get(
        "@purchase/views/purchase_listview"
    );
    if (PurchaseFileUploadListController) {
        PurchaseFileUploadListController.components = {
            ...PurchaseFileUploadListController.components,
            InomDynamicListPanel,
        };
    }
} catch(e) {
    console.warn("[Inom LVM] Purchase patch skipped:", e.message);
}

// 3. HR Expense / Account FileUpload
try {
    const { FileUploadListController } = odoo.loader.modules.get(
        "@account/views/file_upload_list/file_upload_list_controller"
    );
    if (FileUploadListController) {
        FileUploadListController.components = {
            ...FileUploadListController.components,
            InomDynamicListPanel,
        };
    }
} catch(e) {
    console.warn("[Inom LVM] FileUploadListController patch skipped:", e.message);
}