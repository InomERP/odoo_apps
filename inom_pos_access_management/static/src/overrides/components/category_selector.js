/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { CategorySelector } from "@point_of_sale/app/components/category_selector/category_selector";

patch(CategorySelector.prototype, {
    getCategoriesAndSub() {
        const categories = super.getCategoriesAndSub(...arguments);
        const hidden = this.pos.getInomHiddenCategoryIds();
        if (!hidden.size) {
            return categories;
        }
        return categories.filter((c) => !hidden.has(c.id));
    },
});
