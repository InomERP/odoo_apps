import { registry } from "@web/core/registry";
import { Interaction } from "@web/public/interaction";

/** Links inside the request card that open another of its tabs. */
export class PropertyRequestTabs extends Interaction {
    static selector = ".o_property_request";
    dynamicContent = {
        ".o_property_tab_link": { "t-on-click.prevent": this.openTab },
    };

    openTab(ev) {
        this.el.querySelector(`#property_tab_${ev.currentTarget.dataset.tab}`)?.click();
    }
}

registry.category("public.interactions").add("inom_rental_management_website.property_request", PropertyRequestTabs);
