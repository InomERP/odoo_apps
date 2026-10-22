# Real Estate Rental Management - Website (`inom_rental_management_website`)

Publishes properties of `inom_rental_management` on the Odoo website and turns visitor
enquiries into CRM enquiries. Kept as a separate module so the core module does not
require the Website app.

## Requirements

- Odoo 19.0 Community Edition
- `inom_rental_management` and `website_crm` (installs Website and CRM if needed)

## Installation

Install **Real Estate Rental Management - Website** from Apps, or:

```bash
./odoo-bin -c odoo.conf -d <database> -i inom_rental_management_website --stop-after-init
```

Upgrade later with `-u inom_rental_management_website` (always with `-d <database>`).

## Pages

| URL | Content |
| --- | --- |
| `/properties` | Listing with search, rent/sale, category, type, city, bedrooms, price filters and sorting |
| `/properties/<slug>` | Property page: images, key facts, amenities, public description, enquiry form |
| `/properties/brochure/<id>/<token>` | Shareable page for one property, also when unpublished |
| `/contactus` | Standard contact form, creating CRM leads (website_crm) |

A property is shown only when it is **published** (Property Managers only), **active**,
**Available**, belongs to the website's company and is allowed on that website.
Internal description, owner, tenants, contracts, invoices and documents are never rendered.

## Rent and buy requests

The property page has a card with three tabs: **Rent**, **Buy** and **Ask a question**. The tab of the
property's own purpose opens first.

- **Rent** (properties for rent): name, email, phone, preferred move-in date (within 12 months), lease length
  (6, 11, 12, 24 or 36 months), number of occupants and a message.
- **Buy** (properties for sale): name, email, phone, an optional offer, financing (own funds, home loan, not
  decided) and when they want to buy.
- On a property that is not offered that way, the tab says so and links to similar properties that are.

Each request becomes a CRM enquiry (Rent or Sale) with these details on its Property tab and in its notes; a
second request from the same email for the same property updates the open enquiry instead of creating another.
Nothing is booked or paid online: the agent follows up, and **Create Rental Contract** starts the draft lease on
the requested move-in date for the requested length. A purchase offer is shown as the enquiry's asking price.

## 3D view

Each property page has an interactive 3D view with three modes:

- **Exterior**: orbit around the building (drag to rotate, scroll or pinch to zoom, full screen).
- **Interior**: a cut-away "dollhouse" of the floor plan seen from above, with room names and sizes; houses with
  several storeys have a floor switcher.
- **Walk through**: explore at eye height. Drag to look around, walk with W A S D or the arrow keys (Shift to go
  faster), or tap the floor to walk there; room buttons take you straight into a room. Walls stop you, doorways
  let you through.

Set it up on the property's Website tab, under 3D View:

- Upload a **3D Model** as a GLB file (binary glTF 2.0, up to 50 MB) to show your own model of the building,
  with its exterior view and a free walk mode. Most 3D modelling and scanning tools export GLB. It is served only
  to visitors who may see the property.
- Without a model, the page shows an **illustrative model** generated from the property details: the building
  from the 3D Building Style (Automatic picks it from the type and category), Floors in Building and area; the
  interior laid out from the bedrooms, bathrooms and area (apartments and houses), or as an office, shop or
  warehouse; furniture according to the furnishing status. Visitors are told it is illustrative.
- Untick **Show Interior** to show the exterior only, or **Show 3D View** to hide the 3D view.

The viewer uses three.js r147 (MIT, in `static/lib/three`), loaded only when the 3D view scrolls into sight; all
textures are drawn in the browser, so no image files are added. Browsers without WebGL see a short message.

## Tests

```bash
./odoo-bin -c odoo.conf -d <new_test_db> -i inom_rental_management_website \
    --test-enable --test-tags=/inom_rental_management_website --stop-after-init
```
