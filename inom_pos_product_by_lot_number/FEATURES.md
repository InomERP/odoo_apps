# POS Product by Lot/Serial Number — Feature List

**Module:** `inom_pos_product_by_lot_number`
**Version:** 19.0.1.5.3
**Compatible with:** Odoo 19 (Community & Enterprise)
**Depends on:** `point_of_sale`, `stock`, `product`

---

## Features included in this module

| # | Feature | Status | Where it lives |
|---|---------|--------|----------------|
| 1 | **Lot Selection Popup** — when a tracked product is added to the order, a searchable popup opens listing all available lots/serials with name, available qty and expiry date. | ✅ Working | `lot_selection_popup.js/.xml` |
| 2 | **Manual Lot Entry** — type a lot/serial name directly and add it with Enter. | ✅ Working | popup `addManualEntry()` |
| 3 | **Live Autocomplete** — as you type (after N characters), matching lots are fetched from the backend (debounced 300ms) and merged into the list. | ✅ Working | popup `_runRemoteAutocomplete()` + `stock.lot.search_lots_autocomplete` |
| 4 | **Quantity Validation** — when "Strict Quantity Validation" is on, you cannot assign more units of a lot than its available stock; the qty input is capped with an inline error. | ✅ Working | popup `onQtyChange()` |
| 5 | **Real-time Quantity Reflection** — the popup shows *remaining* qty per lot, decremented by any qty already used on other lines of the current order (`avail: N (-M in order)`). | ✅ Working | `pos_store._iml_collectUsedQtyForProduct()` |
| 6 | **Unknown Lot Handling** — typing a name that doesn't exist offers to create it (when lot-creation is enabled) instead of silently failing. | ✅ Working | popup `addManualEntry()` |
| 7 | **Duplicate Serial Prevention** — a serial already used on another line of the order, or already sold historically, is blocked with a red highlight and the Confirm button disabled. | ✅ Working | popup `_validateSerialAsync()` + `stock.lot.check_serial_used` |
| 8 | **Create Lot from POS** — an inline "+ New" form lets authorized users create a new lot/serial without leaving the POS. Protected by a dedicated security group. | ✅ Working | popup `submitCreateLot()` + `stock.lot.create_lot_from_pos` |
| 9 | **Lot vs Serial Logic** — `serial` products force qty = 1 and single selection; `lot` products allow multiple lots and multi-qty; `none` products are untouched. | ✅ Working | popup `isSerial` branching |
| 10 | **Offline Mode** — lots are cached in IndexedDB; lot creation while offline is queued and auto-synced when the connection returns. | ✅ Working | `iml_lot_offline.js` + `stock.lot.sync_offline_lot_creates` |
| 11 | **Receipt Lot Printing** — lot/serial numbers print under each product on the receipt, controllable per POS via a config flag. | ✅ Working | `order_receipt.xml` |
| 12 | **Backend Lot Management** — a Lot/Serial column on POS order lines, plus a "POS Sales" stat-button on the lot form linking to the orders that consumed it. | ✅ Working | `pos_order_views.xml`, `stock_lot_views.xml` |

### Feature currently NOT included

| # | Feature | Status | Reason |
|---|---------|--------|--------|
| – | **Barcode lot-scanning** (scan a lot-number barcode to auto-add its product) | ⛔ Disabled | The Odoo 16/17 `ProductScreen._barcodeLotAction` API used for this was removed/rewritten in Odoo 18/19. It was removed to keep the POS bundle loading cleanly. **Regular product-barcode scanning still works** (that's core Odoo) — you just pick the lot via the popup. Can be re-added once wired to the verified Odoo 19 barcode hook. |

---

## Configuration (per POS)

**Point of Sale → Configuration → Point of Sale → [your POS] → "Lot & Serial Number (POS)" section:**

| Setting | Default | What it does |
|---------|---------|--------------|
| Enable Lot/Serial Scanning | On | (reserved for barcode feature) |
| Show Lot Selection Popup | On | Opens the popup when a tracked product is added |
| Strict Quantity Validation | On | Blocks assigning more than available stock |
| Block Duplicate Serial Numbers | On | Refuses re-used serials |
| Allow Lot Creation from POS | Off | Shows the "+ New" create button |
| Allow Offline Lot Creation | Off | Queues offline creates for sync |
| Print Lot/Serial on Receipt | On | Shows lots on the printed receipt |
| Autocomplete Min Characters | 2 | Chars typed before backend search fires |
| Autocomplete Result Limit | 20 | Max suggestions returned |

## Security

- New group **"POS / Allow Create Lot/Serial Number"** controls who can create lots from POS. POS Managers get it automatically (via post-install hook). Grant it to other users in Settings → Users.
- All RPC methods validate inputs and are company-scoped.

## Backend RPC methods (on `stock.lot`)

- `get_lots_by_product(product_id)` — list available lots for the popup
- `get_lot_by_name(name, product_id)` — exact lookup
- `search_lots_autocomplete(term, product_id, limit)` — fuzzy search
- `create_lot_from_pos(vals)` — group-protected lot creation
- `check_serial_used(lot_name, product_id)` — historical duplicate check
- `sync_offline_lot_creates(batch)` — batch reconnect-sync
- `get_product_and_lot_by_barcode(barcode)` — present for future barcode use
