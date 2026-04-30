/**
 * Expose the active POS configuration's `receipt_design` value to the
 * OrderReceipt OWL component. The XML extension reads this getter and writes
 * it into a `data-design` attribute on the receipt root, which the SCSS then
 * uses to apply the selected layout.
 *
 * The getter walks several possible paths because OrderReceipt is rendered
 * in slightly different contexts (live receipt screen, reprint, printable
 * iframe). Falling back to "classic" keeps the receipt readable even in
 * edge cases where no config is reachable.
 */
import { OrderReceipt } from "@point_of_sale/app/screens/receipt_screen/receipt/order_receipt";
import { patch } from "@web/core/utils/patch";

patch(OrderReceipt.prototype, {
    get receiptDesign() {
        const order = this.props.order || this.props.data?.order;
        const fromOrder =
            order?.config?.receipt_design ??
            order?.config_id?.receipt_design ??
            order?.session_id?.config_id?.receipt_design;
        if (fromOrder) {
            return fromOrder;
        }
        if (this.pos?.config?.receipt_design) {
            return this.pos.config.receipt_design;
        }
        if (this.env?.services?.pos?.config?.receipt_design) {
            return this.env.services.pos.config.receipt_design;
        }
        return "classic";
    },
});
