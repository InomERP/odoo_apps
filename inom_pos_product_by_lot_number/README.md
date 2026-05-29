# inom_pos_product_by_lot_number

**POS Product by Lot / Serial Number — Odoo 19 Custom Module**

[![Odoo](https://img.shields.io/badge/Odoo-19.0-875A7B.svg)](https://www.odoo.com)
[![License: LGPL-3](https://img.shields.io/badge/License-LGPL%203-blue.svg)](https://www.gnu.org/licenses/lgpl-3.0)

A drop-in extension that lets POS cashiers identify, pick, scan, validate, create, and print **Lot/Serial numbers** without leaving the POS interface — and continue working when the network drops.

---

## ✨ Features

| # | Feature | Status |
|---|---------|--------|
| 1 | **Barcode scan** → product auto-added with lot pre-assigned | ✅ |
| 2 | **Selection popup** with searchable, scrollable lot list | ✅ |
| 3 | **Manual entry** + 300ms-debounced autocomplete | ✅ |
| 4 | **Strict quantity validation** against `lot.product_qty` | ✅ |
| 5 | **Real-time qty sync** — popup shows remaining qty net of current order | ✅ |
| 6 | **Unknown-lot prompt** — offers to create the lot in-popup | ✅ |
| 7 | **Duplicate-serial detection** — current order + historical, red highlight | ✅ |
| 8 | **Create Lot from POS** — inline form, group-protected | ✅ |
| 9 | **Tracking-mode aware** — `none`/`lot`/`serial` branched correctly | ✅ |
| 10 | **Offline mode** — IndexedDB cache + sync queue + auto reconnect-flush | ✅ |
| 11 | **Receipt printing** — lot/serial numbers under each product | ✅ |
| 12 | **Backend management** — lot column on POS orders, stat-button on lots | ✅ |

---

## 📦 Installation

1. Drop the `inom_pos_product_by_lot_number/` folder into your Odoo `addons` path.
2. Restart Odoo:
   ```bash
   sudo systemctl restart odoo
   # or
   ./odoo-bin -c odoo.conf -u inom_pos_product_by_lot_number -d <your_db>
   ```
3. In Odoo: **Apps → Update Apps List → search "POS Product by Lot/Serial Number" → Install**.
4. Hard-refresh the POS browser tab (Ctrl + Shift + R) so the new JS bundle loads.

### Module dependencies

- `point_of_sale`
- `stock`
- `product`

All three are part of Community + Enterprise — no extra modules required.

---

## ⚙️ Configuration

### POS-level (per shop)

**Point of Sale → Configuration → Point of Sale → [your config]** → scroll to **"Lot & Serial Number (POS)"**:

| Setting | Default | Purpose |
|---|---|---|
| Enable Lot/Serial Scanning | ✓ | Master switch for barcode lot lookup |
| Show Lot Selection Popup | ✓ | Open popup on tracked-product add |
| Strict Quantity Validation | ✓ | Block over-quantity per lot |
| Block Duplicate Serial Numbers | ✓ | Refuse re-used serials |
| Allow Lot Creation from POS | ✗ | Show "+ New" button in popup |
| Allow Offline Lot Creation | ✗ | Queue creates while offline |
| Print Lot/Serial on Receipt | ✓ | Show lots on the printed receipt |
| Autocomplete Min Characters | 2 | Trigger backend search after N chars |
| Autocomplete Result Limit | 20 | Max suggestions per query |

### Product-level

Each product that participates needs **Inventory tab → Tracking** set to **By Lot** or **By Unique Serial Number**. Products with **No Tracking** are unaffected by this module.

### User-level

Lot creation is gated by the security group **POS / Allow Create Lot/Serial Number**. POS Managers are auto-granted (via post-install hook); to grant to other users:

**Settings → Users & Companies → Users → [user] → Permissions tab** → tick **POS / Allow Create Lot/Serial Number**.

---

## 🧪 Test matrix

Run through this list after install to validate every feature:

| # | Test | Expected |
|---|------|----------|
| 1 | Scan a valid Lot barcode | Product auto-added; lot pre-attached; toast notification |
| 2 | Scan an invalid barcode | Standard "unknown" error (lot fallback didn't match) |
| 3 | Click a tracked product | Popup opens within ~500ms with lots and expiry dates |
| 4 | Select a lot, hit Confirm | Line added; backend `pack_lot_ids` correctly populated |
| 5 | Type 2+ chars in search | List filters locally; backend results merge in after 300ms |
| 6 | Enter qty > lot stock (strict on) | Capped at max; red inline error: "Max available: N" |
| 7 | Add same product twice, same lot | Second popup shows decremented "avail (-N in order)" hint |
| 8 | Type an unknown lot name + Enter | If "Allow Lot Creation" on → create form opens; else "manual" tag |
| 9 | Reuse a sold Serial number | Red row, error message; Confirm button disabled |
| 10 | Enable "Allow Lot Creation" → click + New → fill + Submit | Lot created in backend, immediately selected in popup |
| 11 | Serial-tracked product | Qty input hidden; only one selection allowed; line qty = 1 |
| 12 | Switch off Wi-Fi → click product | Popup still works from IndexedDB cache |
| 13 | Switch off Wi-Fi → create new lot | Toast: "Queued for sync (offline)" — popup proceeds |
| 14 | Switch Wi-Fi back on | Queue auto-flushes within seconds (console: `flushed: N`) |
| 15 | Complete sale | Receipt shows `Lot: XXX` (or `SN: XXX`) under each product |
| 16 | Open POS order in backend | Lines list has a Lot/Serial column with tags |
| 17 | Open Inventory → Lots → a sold lot | Stat-button "POS Sales" shows count; click → linked orders |

---

## 🏗 Architecture

### Backend (Python)

```
models/
├── pos_config.py          → 9 config flags + POS data exposure
├── pos_session.py         → register stock.lot + pos.pack.operation.lot for preload
├── pos_order.py           → placeholder for future order-level lot logic
├── pos_order_line.py      → expose pack_lot_ids to POS frontend
├── pos_pack_operation_lot.py → expose lot_name + relations
├── product_product.py     → expose `tracking` field
└── stock_lot.py           → 6 RPC methods + 1 stat-button action

controllers/main.py        → /inom_pos_lot/ping  + /sync_offline_creates
```

### Frontend (Owl.js)

```
static/src/js/
├── popups/lot_selection_popup.js   → the main Owl component (Dialog-based)
├── overrides/pos_store.js          → addLineToCurrentOrder + barcode handler + offline boot
├── overrides/barcode_reader.js     → ProductScreen lot-fallback patch
└── services/iml_lot_offline.js     → IndexedDB cache + sync queue

static/src/xml/
├── lot_selection_popup.xml         → popup template (Dialog slots)
└── order_receipt.xml               → receipt template extension

static/src/scss/lot_popup.scss      → premium UI styles + mobile rules
```

### Data flow on a tracked-product add

```
ProductScreen.click(product)
   └→ PosStore.addLineToCurrentOrder({product_id, ...})        [patched]
        └→ collect cachedLots from pos.models["stock.lot"]
        └→ augment from IndexedDB                              [Phase 5]
        └→ compute usedInOrder map for the product             [Phase 4]
        └→ open LotSelectionPopup
             └→ user picks lot(s) / creates new / cancels
             └→ getPayload(result)
        └→ super.addLineToCurrentOrder(vals, opts, configure=false)
        └→ create pos.pack.operation.lot records for each picked lot
        └→ set line.qty to total picked qty
```

### Data flow on a barcode scan

```
BarcodeReaderService.scan(barcode)
   └→ ProductScreen._barcodeXxxAction(parsed)                  [patched]
        └→ PosStore.iml_handleLotBarcode(barcode)              [Phase 3]
             └→ ORM call stock.lot.get_product_and_lot_by_barcode
             └→ Find product in pos.models["product.product"]
             └→ PosStore.addLineToCurrentOrder(
                  { product_id }, { iml_pre_selected_lot: { lot_name } }
                )                                              [fast path — no popup]
```

### Offline lifecycle

```
Session start → processServerData() → IMLLotOfflineService boots
  → cacheLots() pushes preloaded stock.lot rows to IndexedDB

window.online   → flushPending() → stock.lot.sync_offline_lot_creates(batch)
window.offline  → iml_createLotFromPos() switches to queueLotCreate()
```

---

## 🔒 Security

- **`stock.lot.create_lot_from_pos`** is hard-gated by `has_group('inom_pos_product_by_lot_number.group_pos_lot_create')`. The `iml_allow_create_lot` config flag is just the UI surface — the group check is the authoritative defence.
- **All RPC methods** validate their inputs (type checks, empty checks, sanitisation). Bad payloads raise `ValidationError` (visible to the user) rather than crashing.
- **Every search is company-scoped** with `('company_id', 'in', (False, env.company.id))`.
- **`sync_offline_lot_creates`** routes through `create_lot_from_pos` so the same group check applies to queued creates as to live ones.
- **Custom controllers** all require `auth='user'`.

---

## 🛠 Customisation hooks

Three places to easily adjust behaviour without forking:

1. **Override the popup** — patch `LotSelectionPopup.prototype` methods (e.g. add custom validation in `confirm()`).
2. **Add new lot RPCs** — extend `stock.lot` from your own module; the POS frontend can call them directly via `this.orm.call("stock.lot", "your_method", [...])`.
3. **Custom barcode types** — extend `ProductScreen._iml_tryLotBarcode(code)` to recognise GS1 AI-10 codes or other formats.

---

## 🐛 Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Popup doesn't appear on click | Config flag off, or product tracking is `none` | Enable **Show Lot Selection Popup**; check product tracking |
| "ir.model.access.csv could not be processed" on install | Old half-installed state | Uninstall first, then install fresh |
| Lots load but qty shows 0 | No quants in the POS source location | Receive stock to the POS source location |
| Receipt doesn't show lots | `iml_print_lot_on_receipt` off OR custom receipt template overrides | Re-enable flag; check that the xpath in `order_receipt.xml` matches your receipt structure |
| Backend order form shows no lot column | View inheritance failed silently | Inspect view via Developer mode → Edit View → "Inherited Views" |
| Offline queue not flushing | Browser blocked IndexedDB (incognito, storage quota) | Switch out of incognito; clear site storage; reload |

Enable verbose console logs by opening DevTools — all warnings are prefixed `[iml_pos_lot]`.

---

## 📂 Module structure

```
inom_pos_product_by_lot_number/
├── __init__.py
├── __manifest__.py
├── README.md
├── controllers/
│   ├── __init__.py
│   └── main.py
├── data/
│   └── pos_config_data.xml
├── models/
│   ├── __init__.py
│   ├── pos_config.py
│   ├── pos_order.py
│   ├── pos_order_line.py
│   ├── pos_pack_operation_lot.py
│   ├── pos_session.py
│   ├── product_product.py
│   └── stock_lot.py
├── security/
│   ├── ir.model.access.csv
│   └── pos_lot_security.xml
├── static/src/
│   ├── js/
│   │   ├── overrides/
│   │   │   ├── barcode_reader.js
│   │   │   └── pos_store.js
│   │   ├── popups/
│   │   │   └── lot_selection_popup.js
│   │   └── services/
│   │       └── iml_lot_offline.js
│   ├── scss/
│   │   └── lot_popup.scss
│   └── xml/
│       ├── lot_selection_popup.xml
│       └── order_receipt.xml
└── views/
    ├── pos_config_views.xml
    ├── pos_order_views.xml
    └── stock_lot_views.xml
```

---

## 📝 License & Author

- **License:** LGPL-3
- **Author:** Inom — https://www.inom-tech.com
- **Version:** 19.0.1.5.0
- **Status:** Production-ready

If you spot a bug or want to contribute, the JS console logs (`[iml_pos_lot] ...`) are the best place to start a report.
