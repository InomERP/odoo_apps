# Manufacturing Order Reset to Draft (`inom_mo_reset`)

Reset **cancelled** Manufacturing Orders back to **Draft** in a single click —
without recreating anything. Product, Bill of Materials, quantities, dates,
responsible person and notes are all preserved; raw material / finished stock
moves are revived to *Draft* and work orders are restored to *To Do*.

* **Odoo version:** 19.0
* **Edition:** Community compatible
* **License:** LGPL-3
* **Depends:** `mrp`, `stock` (chatter via `mail`, brought in by `mrp`)

## Installation

1. Copy the `inom_mo_reset` folder into your Odoo addons path.
2. Restart the Odoo service.
3. Enable *Developer Mode* and update the Apps list.
4. Search for **Manufacturing Order Reset to Draft** and click *Install*.

No configuration is required after installation.

## Usage

1. Open any **Cancelled** Manufacturing Order.
2. Click the **Set to Draft** button in the header.
3. Confirm the dialog — the order instantly returns to *Draft*, fully editable.

The button is only visible on cancelled orders, and only in two cases:

* the **System administrator** sees it automatically, and
* any other user sees it only when an administrator enables the
  **Manufacturing Order Reset** control for them under
  *Settings > Users > Access Rights*.

A plain Manufacturing *User* or *Manager* does **not** see the button unless
that control is enabled for them.

## Running the tests

```bash
odoo -c odoo.conf -d <db> -i inom_mo_reset --test-enable --stop-after-init
```
