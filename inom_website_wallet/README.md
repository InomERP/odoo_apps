# Website Wallet

A complete digital wallet / e-wallet system for Odoo 19 Website.

## Features

- **Wallet Configuration** — enable wallet from `Website > Configuration > Settings`, pick a *Wallet Recharge Product* (a service product) and min/max amounts.
- **Front-end "Wallet" menu** — auto-added to the website main menu, points to `/shop/wallet`.
- **Wallet landing page** (`/shop/wallet`) — shows the current balance and an "Add Wallet Balance" form.
- **Recharge via shop** — entering an amount drops the configured recharge product into the cart at the requested price; checkout flow is unchanged.
- **Auto-credit** — when a sale order containing the recharge product is confirmed, a `credit` wallet transaction is created and the customer's balance is updated.
- **Email notification** — automatic email to the customer on every recharge.
- **Use Wallet on cart** — a "Use Wallet" button appears on the cart page when the customer has positive balance.
- **Customer Portal** — `My Account > Wallet Transactions` shows balance and history.
- **Backend** — `Sales > Configuration > Wallet Transactions` lists every transaction; partner form has a *Wallet Balance* smart button and an *Add Money to Wallet* action.
- **Invoice integration** — customer invoices have an *Add Wallet Balance* header button that applies the available wallet balance as payment.
- **Accounting** — every confirmed transaction creates an `account.payment` on a dedicated *Wallet* journal (auto-created per company).

## Installation

1. Drop the `inom_website_wallet/` folder in your Odoo 19 addons path.
2. Update the apps list (Apps > Update Apps List).
3. Install **Website Wallet**.
4. Configure under `Website > Configuration > Settings > Wallet`:
   - Tick **Use Wallet**.
   - Pick or create a service product as the **Wallet Recharge Product** (e.g. "Wallet Recharge", type *Service*, sale_ok=True).
   - Optionally adjust min/max recharge amounts.
   - Save.

The post-install hook automatically creates a "Wallet" menu in the website main navigation for each website.

## Dependencies

`base`, `mail`, `product`, `account`, `sale_management`, `website`, `website_sale`, `portal`.

## License

LGPL-3
