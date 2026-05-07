# -*- coding: utf-8 -*-
import logging

from odoo import http, _
from odoo.http import request
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


# ----------------------------------------------------------------------
# Version-agnostic cart helpers
#
# In Odoo <= 17, ``request.website.sale_get_order(force_create=True)``
# was the canonical way to fetch the current shopping cart from a
# controller. That method was renamed/removed in Odoo 18+.
#
# To stay compatible across versions, the helpers below try the legacy
# API first, and otherwise look up (or create) the draft sale.order
# directly, mirroring what website_sale itself does internally.
# ----------------------------------------------------------------------
def _get_current_cart():
    """Return the user's current cart (sale.order, possibly empty record set).

    Never creates a new order; returns an empty recordset if there is no
    active draft cart.
    """
    website = request.website
    SaleOrder = request.env['sale.order'].sudo()

    # 1. Legacy API (Odoo <= 17)
    if hasattr(website, 'sale_get_order'):
        try:
            return website.sale_get_order()
        except Exception as e:  # noqa: BLE001
            _logger.debug("Legacy sale_get_order failed: %s", e)

    # 2. Try common Odoo 18+ method names if they exist
    for method_name in (
        '_get_and_check_cart', '_get_cart', '_create_or_get_cart',
        'sale_get_active_order',
    ):
        if hasattr(website, method_name):
            try:
                return getattr(website, method_name)()
            except Exception as e:  # noqa: BLE001
                _logger.debug("%s failed: %s", method_name, e)

    # 3. Direct fallback - look up the order in the session
    order_id = request.session.get('sale_order_id')
    if order_id:
        order = SaleOrder.browse(order_id).exists()
        if order and order.state == 'draft':
            return order
    return SaleOrder


def _get_or_create_cart():
    """Return the user's current cart, creating one if it does not exist."""
    website = request.website
    SaleOrder = request.env['sale.order'].sudo()
    user = request.env.user

    # 1. Legacy API (Odoo <= 17)
    if hasattr(website, 'sale_get_order'):
        try:
            return website.sale_get_order(force_create=True)
        except Exception as e:  # noqa: BLE001
            _logger.debug("Legacy sale_get_order(force_create=True) failed: %s", e)

    # 2. Odoo 18+ method probes
    for method_name in (
        '_get_and_check_cart', '_get_cart', '_create_or_get_cart',
        'sale_get_active_order',
    ):
        if hasattr(website, method_name):
            try:
                return getattr(website, method_name)(force_create=True)
            except TypeError:
                # Method exists but doesn't take force_create
                try:
                    return getattr(website, method_name)()
                except Exception as e:  # noqa: BLE001
                    _logger.debug("%s failed: %s", method_name, e)
            except Exception as e:  # noqa: BLE001
                _logger.debug("%s failed: %s", method_name, e)

    # 3. Direct fallback - find or create
    order = _get_current_cart()
    if order:
        return order

    # Build a new order ourselves
    partner = user.partner_id
    if not partner or partner == request.env.ref(
        'base.public_partner', raise_if_not_found=False
    ):
        # Anonymous - shouldn't happen because our routes require auth='user'
        return SaleOrder

    vals = {
        'partner_id': partner.id,
        'website_id': website.id,
        'company_id': website.company_id.id if website.company_id else request.env.company.id,
    }
    # Optional team / salesperson defined on the website
    if hasattr(website, 'salesteam_id') and website.salesteam_id:
        vals['team_id'] = website.salesteam_id.id
    if hasattr(website, 'salesperson_id') and website.salesperson_id:
        vals['user_id'] = website.salesperson_id.id

    order = SaleOrder.create(vals)
    request.session['sale_order_id'] = order.id
    return order


# ----------------------------------------------------------------------
# Wallet controllers
# ----------------------------------------------------------------------
class WebsiteWalletController(http.Controller):
    """Front-end controller for the customer-facing wallet pages."""

    # ------------------------------------------------------------------
    # JSON endpoint: return wallet info for the front-end injector
    # ------------------------------------------------------------------
    @http.route(['/shop/wallet/info'], type='jsonrpc', auth='user', website=True)
    def wallet_info(self, **kwargs):
        """Used by the front-end widget to decide whether to render the
        "Use Wallet" payment option on the payment page."""
        try:
            if not request.env['res.config.settings'].sudo().is_wallet_enabled():
                return {'enabled': False}
            partner = request.env.user.partner_id.commercial_partner_id
            currency = (
                partner.currency_id
                or request.env.company.currency_id
            )
            # Look at the active cart so the widget can show the right CTA
            try:
                order = _get_current_cart()
            except Exception:
                order = request.env['sale.order']
            amount_total = 0.0
            amount_used = 0.0
            if order and len(order) == 1:
                amount_total = order.amount_total or 0.0
                amount_used = order.wallet_amount_used or 0.0
            amount_remaining = max(amount_total - amount_used, 0.0)
            balance = partner.wallet_balance or 0.0
            if currency.position == 'before':
                balance_formatted = f"{currency.symbol} {balance:.2f}"
            else:
                balance_formatted = f"{balance:.2f} {currency.symbol}"
            return {
                'enabled': True,
                'balance': balance,
                'balance_formatted': balance_formatted,
                'currency_symbol': currency.symbol or currency.name,
                'currency_position': currency.position,
                'order_total': amount_total,
                'wallet_already_applied': amount_used,
                'amount_remaining': amount_remaining,
                'covers_full': amount_remaining > 0 and balance >= amount_remaining,
            }
        except Exception as e:
            _logger.warning("Wallet /shop/wallet/info failed: %s", e)
            return {'enabled': False, 'error': str(e)}

    # ------------------------------------------------------------------
    # Wallet landing page
    # ------------------------------------------------------------------
    @http.route(['/shop/wallet', '/my/wallet'], type='http', auth='user', website=True)
    def wallet_home(self, **kwargs):
        if not request.env['res.config.settings'].sudo().is_wallet_enabled():
            return request.redirect('/shop')
        partner = request.env.user.partner_id.commercial_partner_id
        recharge_product = (
            request.env['res.config.settings'].sudo().get_wallet_recharge_product()
        )
        # Look up the user's current active cart (if any) so we can
        # offer a one-click "Use Wallet" action right from the wallet page.
        try:
            active_cart = _get_current_cart()
        except Exception:
            active_cart = False
        if active_cart and (not active_cart.order_line or active_cart.state != 'draft'):
            active_cart = False
        values = {
            'partner': partner,
            'wallet_balance': partner.wallet_balance,
            'currency': partner.currency_id or request.env.company.currency_id,
            'recharge_product': recharge_product,
            'wallet_enabled': True,
            'active_cart': active_cart,
            'min_amount': float(
                request.env['ir.config_parameter'].sudo().get_param(
                    'inom_website_wallet.wallet_min_recharge', '1'
                )
            ),
            'max_amount': float(
                request.env['ir.config_parameter'].sudo().get_param(
                    'inom_website_wallet.wallet_max_recharge', '10000'
                )
            ),
        }
        return request.render('inom_website_wallet.wallet_landing_page', values)

    # ------------------------------------------------------------------
    # Add Wallet Balance: pushes the recharge product to the cart
    # ------------------------------------------------------------------
    @http.route(['/shop/wallet/recharge'], type='http', auth='user',
                methods=['POST'], website=True, csrf=True)
    def wallet_recharge(self, amount=False, **kwargs):
        if not request.env['res.config.settings'].sudo().is_wallet_enabled():
            return request.redirect('/shop')
        try:
            amount = float(amount or 0.0)
        except (TypeError, ValueError):
            amount = 0.0
        min_amount = float(
            request.env['ir.config_parameter'].sudo().get_param(
                'inom_website_wallet.wallet_min_recharge', '1'
            )
        )
        max_amount = float(
            request.env['ir.config_parameter'].sudo().get_param(
                'inom_website_wallet.wallet_max_recharge', '10000'
            )
        )
        if amount < min_amount or amount > max_amount:
            return request.redirect(
                '/shop/wallet?error=invalid_amount&min=%s&max=%s' % (min_amount, max_amount)
            )

        recharge_product = (
            request.env['res.config.settings'].sudo().get_wallet_recharge_product()
        )
        if not recharge_product:
            return request.redirect('/shop/wallet?error=no_product')

        # Get / build cart (version-agnostic)
        order = _get_or_create_cart()
        if not order:
            return request.redirect('/shop/wallet?error=no_product')
        # Add the line with the user-specified price
        order_line = order.order_line.filtered(
            lambda l: l.product_id.id == recharge_product.id
        )
        if order_line:
            # Update the existing recharge line price to match the latest amount
            order_line[0].sudo().write({
                'product_uom_qty': 1,
                'price_unit': amount,
            })
        else:
            request.env['sale.order.line'].sudo().create({
                'order_id': order.id,
                'product_id': recharge_product.id,
                'product_uom_qty': 1,
                'price_unit': amount,
                'name': _('Wallet Recharge - %s', amount),
            })
        return request.redirect('/shop/cart')

    # ------------------------------------------------------------------
    # Shop: pay the cart with the wallet balance
    # ------------------------------------------------------------------
    @http.route(['/shop/wallet/use'], type='http', auth='user',
                methods=['POST'], website=True, csrf=True)
    def wallet_use_on_cart(self, **kwargs):
        if not request.env['res.config.settings'].sudo().is_wallet_enabled():
            return request.redirect('/shop/payment')
        order = _get_current_cart()
        if not order or not order.order_line:
            return request.redirect('/shop/payment')
        partner = order.partner_id.commercial_partner_id or order.partner_id
        balance = partner.wallet_balance
        if balance <= 0:
            return request.redirect('/shop/payment?error=no_balance')

        try:
            order.sudo().action_pay_with_wallet()
        except UserError as e:
            _logger.info("Wallet usage on order %s failed: %s", order.name, e)
            return request.redirect('/shop/payment?error=wallet_failed')

        # If wallet fully covered the order, confirm the order and redirect
        # to the confirmation page.
        if order.amount_total - (order.wallet_amount_used or 0.0) <= 0.001:
            try:
                order.sudo().action_confirm()
            except Exception as e:  # noqa: BLE001
                _logger.warning("Order confirmation after wallet pay failed: %s", e)
            request.session['sale_last_order_id'] = order.id
            return request.redirect('/shop/confirmation')
        # Otherwise return to the payment page; remaining due must be paid
        # via another method.
        return request.redirect('/shop/payment')
