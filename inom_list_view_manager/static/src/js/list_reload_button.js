/** @odoo-module **/
import { patch } from "@web/core/utils/patch";
import { render } from "@web/owl2/utils";
import { ListController } from "@web/views/list/list_controller";
patch(ListController.prototype, {

    setup() {
        super.setup(...arguments);
        setTimeout(() => {
            const columnsBtn = [...document.querySelectorAll("button")]
                .find(btn => btn.innerText?.trim().includes("Columns"));
            if (!columnsBtn) {
                return;
            }
            if (document.querySelector(".o_reload_list_btn")) {
                return;
            }

            const reloadBtn = document.createElement("button");

            reloadBtn.className =
                "btn btn-secondary o_reload_list_btn";

            reloadBtn.innerHTML =
                `<i class="fa fa-refresh"></i>`;

            reloadBtn.title = "Reload Data";

            reloadBtn.style.marginLeft = "4px";

            reloadBtn.onclick = async () => {


                try {

                    await this.model.root.load();

                    render(this, true);


                } catch (e) {

                    console.error("RELOAD ERROR", e);
                }
            };

            columnsBtn.insertAdjacentElement(
                "afterend",
                reloadBtn
            );
        }, 2000);
    },
});
