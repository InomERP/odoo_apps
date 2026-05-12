# Quick Form Drawer (`inom_quick_form_drawer`)

Adds a generic **eye icon** to every row in every list view across Odoo 19.
Clicking the icon slides a drawer in from the right showing the record's
form view — viewable **and editable**, with save, discard, statusbar
buttons and chatter all working normally.

> Author: **InomERP Pvt Ltd** · ✉️ info@inomerp.in · 🌐 https://inomerp.in

## Installation

1. Copy the `inom_quick_form_drawer` folder into your Odoo addons path.
2. Restart the Odoo service (with `--dev=all` during development helps).
3. Activate developer mode → **Apps** → **Update Apps List**.
4. Search for **Quick Form Drawer** and click **Install**.
5. **Hard-refresh** your browser (Ctrl + Shift + R) so the new JS / SCSS assets load.

## Verifying the install

Open any list view (e.g. Sales → Quotations) and open the browser console
(F12 → Console). You will not see any error from this module. Each row
in the list table should now have an eye icon at the right end of the row.
Clicking it opens a slide-in drawer showing the form view of that record.

If the eye icon does not appear after a hard refresh, try a full asset
rebuild by visiting `/web?debug=assets` once.

## Module structure

```
inom_quick_form_drawer/
├── __init__.py
├── __manifest__.py
├── README.md
└── static/
    ├── description/        # Odoo Apps Store assets (icon, banner, html)
    └── src/
        ├── record_drawer_service.js
        ├── list_renderer/
        │   └── list_renderer.js          # patches ListRenderer, injects eye column
        └── record_drawer/
            ├── record_drawer.js          # OWL component
            ├── record_drawer.xml
            └── record_drawer.scss
```

## How it works

| Layer                | File                                              | Responsibility                                                                                            |
|----------------------|---------------------------------------------------|-----------------------------------------------------------------------------------------------------------|
| Service              | `static/src/record_drawer_service.js`             | Reactive state (`isOpen`, `resModel`, `resId`) + `open()` / `close()` API.                                |
| ListRenderer patch   | `static/src/list_renderer/list_renderer.js`       | Uses OWL `onMounted` / `onPatched` hooks to inject an eye-icon column into the rendered list table DOM.   |
| Drawer component     | `static/src/record_drawer/*`                      | OWL component registered as `main_components` entry; embeds `<View type="form">`.                         |

### Why DOM injection?

The first version used QWeb t-inherit template inheritance with
`hasclass('o_data_row')`, but in Odoo 18+/19 the data row's class is set
dynamically via `t-att-class`, so `hasclass()` did not match and the
inheritance silently produced nothing. Injecting against the rendered DOM
sidesteps this entirely.

## Customization

### Drawer width

Override in your own theme:

```scss
.o_record_drawer {
    width: 800px;   /* default is 640px */
}
```

## Support

- 🌐 Website: https://inomerp.in
- ✉️ Email: info@inomerp.in

## License

LGPL-3
