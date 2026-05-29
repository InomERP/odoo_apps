# Simplify POS Access Management

**Module name:** `inom_pos_access_management`
**Odoo version:** 17.0 (Community / Enterprise)
**Author:** Terabits Technolab
**License:** LGPL-3

---

## 1. Overview

Create access rules for multiple users and employees of the **Point of Sale**.
With a single click you can hide or disable specific POS buttons — no technical
skills required.

The module ships **31 toggles** organised into 7 categories:

| Category               | Toggles |
|------------------------|---------|
| Salesperson            | 2       |
| Payment                | 7       |
| Order                  | 3       |
| Customer               | 3       |
| Numpad                 | 5       |
| Action                 | 7       |
| General                | 4       |

---

## 2. Installation

1. Place the `inom_pos_access_management` folder inside your Odoo addons path.
2. Update the apps list:
   *Apps → Update Apps List*.
3. Install **Simplify POS Access Management**.
4. The dependencies (`point_of_sale`, `hr`, `mail`, `stock`, `account`, `sale`)
   are installed automatically if not already present.

---

## 3. Setup & Configuration

### 3.1 Enable "POS Management Permission" on a user

`Settings → Users & Companies → Users → (open user) → POS Access Management tab`

Toggle **POS Management Permission**.

### 3.2 Create an access rule

`Point of Sale → Configuration → POS Access Rights → Create`

* Pick the **User** (required) and optional **Employee**.
* Switch to any of the seven tabs and toggle the features you want hidden /
  disabled.
* Save — the rule is applied the next time the user opens a POS session.

---

## 4. Feature Reference

### 4.1 Salesperson (2)
- `Salesperson can only see his orders`
- `Salesperson can only see his customers`

### 4.2 Payment (7)
- `Hide Payment Button`
- `Restrict Payment Method` (+ choose allowed methods)
- `Hide Customer Button (Payment Screen)`
- `Hide Payment Validate Button`
- `Hide Payment Tip Button`
- `Hide Payment Ship Later Button`
- `Hide Payment Invoice Button`

### 4.3 Order (3)
- `Restrict POS Categories` (+ choose hidden categories)
- `Hide Delete Order Button`
- `Only Show Active Order`

### 4.4 Customer (3)
- `Hide Customer Button`
- `Hide Create Customer Button`
- `Hide Save Customer Button`

### 4.5 Numpad (5)
- `Hide Numpad Buttons`
- `Disable Price Button`
- `Disable Qty Button`
- `Disable Discount Button`
- `Disable (+/-) Button`

### 4.6 Action (7)
- `Hide Customer Note Button`
- `Hide Refund Button`
- `Hide Info Button`
- `Hide Quotation Button`
- `Hide Fiscal Button`
- `Hide Price List Button`
- `Hide Transfer Button`

### 4.7 General (4)
- `Hide Close POS Button`
- `Hide Backend POS Button`
- `Hide Cash In/Out POS Button`
- `Hide Debug Window`

---

## 5. Technical Notes

* New model: `pos.access.rights` (one rule per user).
* Patches `res.users`, `pos.session`, `pos.order`, `res.partner` for
  server-side filtering of orders / customers (salesperson restrictions).
* OWL component overrides in `static/src/overrides/**` apply UI restrictions.
* The POS frontend loads each user's rule via the Odoo-17 POS data pipeline
  on `pos.session`:
  `_pos_ui_models_to_load` + `_loader_params_pos_access_rights` +
  `_get_pos_ui_pos_access_rights`.
* No tracked or external dependencies beyond the standard Odoo CE addons.

---

## 6. Compatibility

| Platform     | Supported |
|--------------|-----------|
| Odoo Online  | ✅        |
| Odoo.sh      | ✅        |
| On-Premise   | ✅        |

Tested with **Odoo 17.0 Community** and **Enterprise** editions.

---

## 7. Migration history

This is the Odoo-17 port of the original Odoo-18 module. The key
adaptations were:

| Concern                           | Odoo 18 (original)                           | Odoo 17 (this version)                                                                    |
|-----------------------------------|----------------------------------------------|-------------------------------------------------------------------------------------------|
| POS data loading                  | `_inherit = ['pos.load.mixin']` + `_load_pos_data_*` on the model | `_pos_ui_models_to_load` + `_loader_params_<m>` + `_get_pos_ui_<m>` on `pos.session`      |
| Pos-order pre-filter              | `pos.order._load_pos_data_domain`            | `pos.order.search_paid_order_ids` override                                                |
| Pos-partner pre-filter            | `res.partner._load_pos_data_domain`          | `pos.session._loader_params_res_partner` (auto-covers initial load + on-demand search)    |
| `SELF_*_FIELDS` extension         | `@property` chained via `super`              | `__init__` class-attribute extension (required — Odoo 17 base reads `type(self).SELF_*`)  |
| List view tag                     | `<list>`                                     | `<tree>`                                                                                  |
| Action `view_mode`                | `list,form`                                  | `tree,form`                                                                               |
| PosStore data exposure (JS)       | `this.models["pos.access.rights"].getAll()`  | `this.pos_access_rights` (populated in `_processData` override)                           |
| `accessRule.user_id` shape (JS)   | resolved record `{id, name}`                 | search_read tuple `[id, name]` — normalised via the `_m2oId` helper                       |
| `restrict_*_ids` Many2many (JS)   | resolved record objects                      | raw integer ids — normalisation handles both shapes                                       |

Every other line of code, every CSS selector and every behaviour from
the Odoo-18 module is preserved as-is.

---

## 8. Restaurant Add-on

If you need restrictions for the restaurant module (Split / Bill / Internal
Note / Guest / Floors / Order buttons), install the separate
`pos_restaurant_access_management` add-on.
