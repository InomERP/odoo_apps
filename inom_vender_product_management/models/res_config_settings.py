# -*- coding: utf-8 -*-
from odoo import api, fields, models

from .vendor_import_settings import (
    DEFAULT_PRODUCT_HELP,
    DEFAULT_STOCK_HELP,
    IMPORT_KINDS,
)

TEMPLATE_MIMETYPES = [
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'application/vnd.ms-excel',
]

#: field name on res.config.settings -> import kind, for the two Html help
#: texts. They are stored by hand because res.config.settings' generic
#: `config_parameter` support only covers scalar field types.
HELP_FIELDS = {
    'vendor_product_import_help': 'product',
    'vendor_stock_import_help': 'stock',
}


def _default_attachment(kind):
    """Default for a template setting: the id of the attachment the module
    ships with, or False when it is missing."""
    xml_id = IMPORT_KINDS[kind][2]

    def _default(self):
        record = self.env.ref(xml_id, raise_if_not_found=False)
        return record.id if record else False

    return _default


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    group_vendor_product_portal = fields.Boolean(
        string="Vendor Products Portal",
        implied_group='inom_vender_product_management.group_vendor_product_portal',
        group='base.group_portal',
        help="Turn on to let vendors manage products in the Odoo portal by themselves.",
    )
    group_vendor_stock_portal = fields.Boolean(
        string="Vendor Stocks in Portal",
        implied_group='inom_vender_product_management.group_vendor_stock_portal',
        group='base.group_portal',
        help="Let vendors observe, manage, and import their stock levels.",
    )

    vendor_product_import_template_id = fields.Many2one(
        'ir.attachment',
        string="Template for vendor products import",
        config_parameter=IMPORT_KINDS['product'][0],
        default=_default_attachment('product'),
        domain=[('mimetype', 'in', TEMPLATE_MIMETYPES)],
        help="This attachment will be shown for users as a template for the "
             "table to import vendor products. Make sure it is public.",
    )
    vendor_stock_import_template_id = fields.Many2one(
        'ir.attachment',
        string="Template for vendor stocks import",
        config_parameter=IMPORT_KINDS['stock'][0],
        default=_default_attachment('stock'),
        domain=[('mimetype', 'in', TEMPLATE_MIMETYPES)],
        help="This attachment will be shown for users as a template for the "
             "table to import vendor stocks. Make sure it is public.",
    )

    vendor_product_import_help = fields.Html(
        string="Help text for importing vendor products",
        sanitize=False,
        help="Shown on the Help tab of the Import Vendor Products wizard and "
             "on the vendor's portal import page.",
    )
    vendor_stock_import_help = fields.Html(
        string="Help text for importing vendor stocks",
        sanitize=False,
        help="Shown on the Help tab of the Import Vendor Stocks wizard and "
             "on the vendor's portal import page.",
    )

    @api.model
    def get_values(self):
        res = super().get_values()
        Settings = self.env['vendor.import.settings']
        for fname, kind in HELP_FIELDS.items():
            res[fname] = Settings.get_help_html(kind)
        return res

    def set_values(self):
        super().set_values()
        # sudo: ir.config_parameter is restricted to system users; only the
        # module's own two help-text keys are written here, from a Settings
        # form that only administrators can open.
        ICP = self.env['ir.config_parameter'].sudo()
        Settings = self.env['vendor.import.settings']
        defaults = {'product': DEFAULT_PRODUCT_HELP, 'stock': DEFAULT_STOCK_HELP}
        for fname, kind in HELP_FIELDS.items():
            value = self[fname]
            # An emptied editor means "go back to the shipped help text"
            # rather than "show nothing at all".
            ICP.set_str(
                Settings._help_param(kind),
                str(value) if value else defaults[kind],
            )
