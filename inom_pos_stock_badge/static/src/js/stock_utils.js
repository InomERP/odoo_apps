/** @odoo-module **/
import { _t } from "@web/core/l10n/translation";

/**
 * product.template id of a product.template or product.product record.
 */
export function getTemplateId(product) {
    if (!product) {
        return null;
    }
    const tmpl = product.product_tmpl_id;
    if (tmpl) {
        return typeof tmpl === "object" ? tmpl.id : tmpl;
    }
    return product.id ?? null;
}

/**
 * Configured stock qty of a product (aggregated per template), or null when
 * the product is not stock-tracked or stock has not been loaded yet.
 */
export function getStockQty(pos, product) {
    const tmplId = getTemplateId(product);
    if (tmplId === null || !pos?.stockMap) {
        return null;
    }
    const qty = pos.stockMap[tmplId];
    return typeof qty === "number" ? qty : null;
}

/**
 * Quantity of the given template already in ``order`` (positive lines only).
 */
function getQtyInOrder(order, tmplId, excludeLine) {
    let total = 0;
    for (const line of order?.lines || []) {
        if (line === excludeLine || getTemplateId(line.product_id) !== tmplId) {
            continue;
        }
        if (line.qty > 0) {
            total += line.qty;
        }
    }
    return total;
}

/**
 * Check whether ``qtyToAdd`` more units of ``product`` may be added to ``order``.
 * Returns ``{ title, body }`` when the operation must be blocked, null otherwise.
 *
 * @param {Object} pos
 * @param {Object} product product.template or product.product record
 * @param {Number} qtyToAdd
 * @param {Object} [options]
 * @param {Object} [options.order] order to count already-added qty from
 * @param {Object} [options.excludeLine] line whose current qty must not be counted
 */
export function checkStock(pos, product, qtyToAdd, { order = null, excludeLine = null } = {}) {
    const cfg = pos?.config;
    if (!cfg?.display_stock || !product || !(qtyToAdd > 0)) {
        return null;
    }
    const allowOutOfStock = cfg.allow_order_out_of_stock;
    const denyBelowQty = Number(cfg.deny_order_below_qty) || 0;
    if (allowOutOfStock && denyBelowQty <= 0) {
        return null;
    }
    const stock = getStockQty(pos, product);
    if (stock === null) {
        return null;
    }

    const tmplId = getTemplateId(product);
    const inOrder = order ? getQtyInOrder(order, tmplId, excludeLine) : 0;
    const total = inOrder + qtyToAdd;
    const name = product.display_name || product.name || "";

    if (!allowOutOfStock) {
        if (stock <= 0) {
            return {
                title: _t("Out of Stock"),
                body: _t('"%s" is out of stock. This product cannot be added to the order.', name),
            };
        }
        if (total > stock) {
            const body = inOrder > 0
                ? _t('Cannot add more "%(name)s". Available stock: %(stock)s unit(s), already in cart: %(inOrder)s.', { name, stock, inOrder })
                : _t('Cannot add more "%(name)s". Available stock: %(stock)s unit(s).', { name, stock });
            return { title: _t("Insufficient Stock"), body };
        }
    }
    if (denyBelowQty > 0 && stock - total <= denyBelowQty) {
        return {
            title: _t("Stock Limit Reached"),
            body: _t(
                'Cannot add "%(name)s". Remaining stock would be %(remaining)s, at or below the minimum allowed quantity (%(min)s).',
                { name, remaining: stock - total, min: denyBelowQty }
            ),
        };
    }
    return null;
}
