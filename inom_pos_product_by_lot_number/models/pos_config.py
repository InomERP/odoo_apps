# -*- coding: utf-8 -*-
from odoo import api, fields, models


class PosConfig(models.Model):
    """
    Extends pos.config with all POS Lot/Serial-Number settings.
    Every behaviour in the frontend is gated by one of these flags so
    the module remains opt-in and tunable per-shop.
    """
    _inherit = 'pos.config'

    # ─────────────────────────────────────────────────────────────────────
    # FEATURE TOGGLES
    # ─────────────────────────────────────────────────────────────────────

    iml_enable_lot_scanning = fields.Boolean(
        string="Enable Lot/Serial Scanning",
        default=True,
        help="Allow scanning Lot/Serial numbers via barcode to add products "
             "to the cart (Feature 1).",
    )

    iml_enable_lot_popup = fields.Boolean(
        string="Show Lot Selection Popup",
        default=True,
        help="When a tracked product is added, show a popup to select the "
             "lot/serial number (Feature 2).",
    )

    iml_allow_create_lot = fields.Boolean(
        string="Allow Lot Creation from POS",
        default=False,
        help="Allow cashiers to create new lots/serial numbers directly from "
             "the POS interface (Feature 8). Disable for stricter inventory control.",
    )

    iml_print_lot_on_receipt = fields.Boolean(
        string="Print Lot/Serial on Receipt",
        default=True,
        help="Display the Lot/Serial number(s) of each product on the customer "
             "receipt and invoice (Feature 11).",
    )

    iml_strict_qty_validation = fields.Boolean(
        string="Strict Quantity Validation",
        default=True,
        help="Block adding more units than the lot has available stock "
             "(Feature 4).",
    )

    iml_check_duplicate_serial = fields.Boolean(
        string="Block Duplicate Serial Numbers",
        default=True,
        help="Prevent the same Serial number from being used multiple times "
             "within the session or in historical orders (Feature 7).",
    )

    iml_allow_offline_lot_create = fields.Boolean(
        string="Allow Offline Lot Creation",
        default=False,
        help="Queue lot creations made in offline mode and sync them on reconnect "
             "(Feature 10).",
    )

    # ─────────────────────────────────────────────────────────────────────
    # AUTOCOMPLETE TUNING
    # ─────────────────────────────────────────────────────────────────────

    iml_lot_autocomplete_min_chars = fields.Integer(
        string="Autocomplete Min Characters",
        default=2,
        help="Minimum characters typed before showing autocomplete suggestions "
             "(Feature 3).",
    )

    iml_lot_autocomplete_limit = fields.Integer(
        string="Autocomplete Result Limit",
        default=20,
        help="Maximum number of lot suggestions returned by the autocomplete search.",
    )

    # ─────────────────────────────────────────────────────────────────────
    # POS DATA EXPOSURE
    # ─────────────────────────────────────────────────────────────────────

    @api.model
    def _load_pos_data_fields(self, *args, **kwargs):
        """Expose our config flags to the POS frontend so it can branch on them.

        VERSION-SAFE (Odoo 18 + 19):
        In Odoo 18, pos.config does NOT define _load_pos_data_fields, so super()
        resolves to the pos.load.mixin which returns [] — and an EMPTY list means
        "load ALL fields" (our iml_* fields are therefore already included).
        Appending names to [] would RESTRICT the read to only those names,
        dropping use_pricelist / currency_id / ... and crashing load_data
        ("Cannot convert undefined or null to object" at boot). So we only extend
        when the base already lists explicit fields (the Odoo 19 behaviour).
        """
        fields_list = super()._load_pos_data_fields(*args, **kwargs)
        if not fields_list:
            # Odoo 18: [] already means all fields -> nothing to add.
            return fields_list
        extra = [
            'iml_enable_lot_scanning',
            'iml_enable_lot_popup',
            'iml_allow_create_lot',
            'iml_print_lot_on_receipt',
            'iml_strict_qty_validation',
            'iml_check_duplicate_serial',
            'iml_allow_offline_lot_create',
            'iml_lot_autocomplete_min_chars',
            'iml_lot_autocomplete_limit',
        ]
        for f in extra:
            if f not in fields_list:
                fields_list.append(f)
        return fields_list
