/** Advanced DMS Odoo 20 - reliable V19-style card actions. */
(function () {
    "use strict";

    function closeMenus(except) {
        document.querySelectorAll('.o_edm_action_menu.show').forEach(function (menu) {
            if (menu !== except) {
                menu.classList.remove('show');
                var btn = menu.querySelector('.o_edm_action_menu_btn');
                if (btn) btn.setAttribute('aria-expanded', 'false');
            }
        });
    }

    document.addEventListener('click', function (ev) {
        var button = ev.target.closest('.o_edm_action_menu_btn');
        if (button) {
            ev.preventDefault();
            ev.stopPropagation();
            var menu = button.closest('.o_edm_action_menu');
            if (!menu) return;
            var open = menu.classList.contains('show');
            closeMenus(menu);
            menu.classList.toggle('show', !open);
            button.setAttribute('aria-expanded', String(!open));
            return;
        }

        if (!ev.target.closest('.o_edm_action_menu')) {
            closeMenus(null);
        }
    }, true);

    document.addEventListener('keydown', function (ev) {
        if (ev.key === 'Escape') closeMenus(null);
    });
})();
