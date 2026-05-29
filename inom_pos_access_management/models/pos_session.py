# -*- coding: utf-8 -*-
from odoo import models, api


class PosSession(models.Model):
    """Hook ``pos.access.rights`` and the salesperson-customer restriction
    into the Odoo-17 POS data-loading pipeline.

    Odoo 17 vs Odoo 18
    ------------------
    Odoo 17 uses a triple-method protocol on ``pos.session`` to ship
    arbitrary data to the POS frontend:

        ``_pos_ui_models_to_load(self)``
            Return the list of model names that should be loaded.

        ``_loader_params_<model_name>(self)``
            Return ``{'search_params': {'domain': ..., 'fields': ...}}``.

        ``_get_pos_ui_<model_name>(self, params)``
            Return the records (usually via ``search_read(**params['search_params'])``).

    Odoo 18 replaced this with ``pos.load.mixin`` and the
    ``_load_pos_data_*`` family declared directly on each model.
    The user-facing semantics are identical; only the wiring differs.

    For the salesperson-customer restriction the same
    ``_loader_params_res_partner`` hook is automatically reused by
    ``get_pos_ui_res_partner_by_params`` (the on-demand customer-search
    RPC used from the partner-list screen), so the filter applies both at
    initial load AND on subsequent searches — no separate override needed.
    """
    _inherit = 'pos.session'

    # Fields shipped to the POS JS layer for each pos.access.rights row.
    _POS_ACCESS_RIGHTS_FIELDS = [
        'id', 'name', 'user_id', 'employee_id', 'active',
        # Salesperson
        'restrict_salesperson_orders', 'restrict_salesperson_customers',
        # Payment
        'hide_payment_button', 'restrict_payment_method',
        'restrict_payment_method_ids',
        'hide_payment_customer_button', 'hide_payment_validate_button',
        'hide_payment_tip_button', 'hide_payment_ship_later_button',
        'hide_payment_invoice_button',
        # Order
        'restrict_pos_categories', 'restrict_pos_category_ids',
        'hide_delete_order_button', 'only_show_active_order',
        # Customer
        'hide_customer_button', 'hide_create_customer_button',
        'hide_save_customer_button',
        # Numpad
        'hide_numpad_buttons', 'disable_price_button', 'disable_qty_button',
        'disable_discount_button', 'disable_plus_minus_button',
        # Action
        'hide_customer_note_button', 'hide_refund_button', 'hide_info_button',
        'hide_quotation_button', 'hide_fiscal_button', 'hide_pricelist_button',
        'hide_transfer_button',
        # General
        'hide_close_pos_button', 'hide_backend_pos_button',
        'hide_cash_in_out_button', 'hide_debug_window',
    ]

    # ------------------------------------------------------------------
    # 1. Register the model with the POS loader
    # ------------------------------------------------------------------
    @api.model
    def _pos_ui_models_to_load(self):
        result = super()._pos_ui_models_to_load()
        if 'pos.access.rights' not in result:
            result.append('pos.access.rights')
        return result

    # ------------------------------------------------------------------
    # 2. Search params (= domain + fields) for pos.access.rights
    # ------------------------------------------------------------------
    def _loader_params_pos_access_rights(self):
        """Only the access rule of the current user is shipped to the
        frontend. Mirrors the Odoo-18 ``_load_pos_data_domain`` /
        ``_load_pos_data_fields`` pair.
        """
        return {
            'search_params': {
                'domain': [
                    ('user_id', '=', self.env.uid),
                    ('active', '=', True),
                ],
                'fields': list(self._POS_ACCESS_RIGHTS_FIELDS),
            },
        }

    # ------------------------------------------------------------------
    # 3. Actual record fetch for pos.access.rights
    # ------------------------------------------------------------------
    def _get_pos_ui_pos_access_rights(self, params):
        # ``sudo()`` is safe here: the domain is already locked to the
        # current user, and group_pos_user has read on the model.
        return self.env['pos.access.rights'].sudo().search_read(
            **params['search_params']
        )

    # ------------------------------------------------------------------
    # 4. Salesperson-customer restriction (initial load + on-demand search)
    #
    # ``get_pos_ui_res_partner_by_params`` (called by the POS partner-list
    # search RPC) re-uses ``_loader_params_res_partner`` to obtain the
    # base search params, so overriding the latter automatically covers
    # both the initial customer load AND every on-demand partner search.
    # ------------------------------------------------------------------
    def _loader_params_res_partner(self):
        params = super()._loader_params_res_partner()
        access = self.env['pos.access.rights'].sudo().search([
            ('user_id', '=', self.env.uid),
            ('active', '=', True),
        ], limit=1)
        if access and access.restrict_salesperson_customers:
            base_domain = list(params.get('search_params', {}).get('domain') or [])
            params.setdefault('search_params', {})['domain'] = base_domain + [
                ('user_id', '=', self.env.uid),
            ]
        return params
