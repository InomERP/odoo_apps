# -*- coding: utf-8 -*-
"""Single place that knows how the configurable import settings are stored.

Everything else in the module (the two import wizards, the portal
controllers, the Configuration menu entries) reads the templates and the
help texts through this helper, so there is exactly one definition of the
parameter keys and of the fallbacks used when nothing is configured yet.
"""
from markupsafe import Markup

from odoo import api, models

MODULE = 'inom_vender_product_management'

#: Kind -> (config parameter key for the attachment,
#:          config parameter key for the help text,
#:          xml id of the attachment shipped with the module)
IMPORT_KINDS = {
    'product': (
        '%s.vendor_product_import_template_id' % MODULE,
        '%s.vendor_product_import_help' % MODULE,
        '%s.attachment_vendor_product_import_template' % MODULE,
    ),
    'stock': (
        '%s.vendor_stock_import_template_id' % MODULE,
        '%s.vendor_stock_import_help' % MODULE,
        '%s.attachment_vendor_stock_import_template' % MODULE,
    ),
}

DEFAULT_PRODUCT_HELP = """<h4>While preparing the table for import, please take into account:</h4>
<ul>
    <li>The columns in the template are strictly defined. Do not re-arrange and do not remove them.</li>
    <li>The column <b>Vendor Product Name</b> must be filled up. Other columns are optional.</li>
    <li>There should be no empty lines. The first line is always a line with headers, lines with real data should start from line 2.</li>
    <li><b>Vendor Product Code</b> is the vendor's own reference. It is used to match existing lines on re-import, so keep it consistent between imports.</li>
    <li><b>Internal Product Reference</b> is the internal reference of your own product, used to auto-match the vendor line to it.</li>
    <li>Prices should have a proper number format in all cells.</li>
    <li>The option 'Archive other products of this vendor' will lead to previous products being archived.</li>
    <li>The option 'Mark previous prices as outdated' will lead to previous products' prices being flagged as outdated.</li>
</ul>"""

DEFAULT_STOCK_HELP = """<h4>While preparing the table for import, please take into account:</h4>
<ul>
    <li>The columns in the template are strictly defined. Do not re-arrange and do not remove them.</li>
    <li>The columns <b>Vendor Product Code</b>, <b>Vendor Location</b> and <b>Quantity</b> must be filled up.</li>
    <li>The vendor product code must already exist for this vendor - import the products first if needed.</li>
    <li>A vendor location that does not exist yet is created automatically.</li>
    <li>There should be a single line for each combination product - location.</li>
    <li>The first line is always a line with headers, lines with real data should start from line 2. There should be no empty lines.</li>
    <li>Quantities should have a proper number format in all cells.</li>
    <li><b>Vendor UoM</b> is optional and must be chosen among the list of available units of measure in Odoo. It defaults to the matched product's unit of measure.</li>
    <li>The option 'Archive other products of this vendor' will lead to previous products being archived.</li>
    <li>The option 'Archive previous stocks of this vendor' will lead to previous stock levels being archived.</li>
</ul>"""

DEFAULT_HELP = {
    'product': DEFAULT_PRODUCT_HELP,
    'stock': DEFAULT_STOCK_HELP,
}


class VendorImportSettings(models.AbstractModel):
    """Read-side accessor for the import configuration.

    Abstract on purpose: it carries no data of its own and needs no access
    rules, so portal controllers can call it just as freely as the backend
    wizards can.
    """
    _name = 'vendor.import.settings'
    _description = 'Vendor Import Settings'

    @api.model
    def _template_param(self, kind):
        return IMPORT_KINDS[kind][0]

    @api.model
    def _help_param(self, kind):
        return IMPORT_KINDS[kind][1]

    @api.model
    def _default_template(self, kind):
        """The attachment shipped with the module, used until an admin picks
        another one in the settings."""
        return self.env.ref(IMPORT_KINDS[kind][2], raise_if_not_found=False) or \
            self.env['ir.attachment']

    @api.model
    def get_template_attachment(self, kind):
        """Return the configured import template as a sudo'd ir.attachment.

        Falls back to the attachment shipped with the module when the
        setting is empty or points at a record that has been deleted.
        """
        # sudo: read-only. ir.config_parameter is restricted to system
        # users, and the template attachment must be readable by purchase
        # users and portal vendors alike; only the module's own template
        # key and the attachment it points at are ever read here.
        param = self.env['ir.config_parameter'].sudo().get_str(self._template_param(kind))
        attachment = self.env['ir.attachment'].sudo()
        if param:
            try:
                attachment = attachment.browse(int(param)).exists()
            except (TypeError, ValueError):
                # sudo: same read-only attachment lookup as above.
                attachment = self.env['ir.attachment'].sudo()
        # sudo: fall back to the template shipped with the module (read-only).
        return attachment or self._default_template(kind).sudo()

    @api.model
    def get_help_html(self, kind):
        """Return the configured help text for an import, as safe markup."""
        # sudo: read-only access to the module's own help-text key;
        # ir.config_parameter is restricted to system users, but the help is
        # shown to purchase users and portal vendors.
        value = self.env['ir.config_parameter'].sudo().get_str(self._help_param(kind))
        if value in (None, False, ''):
            value = DEFAULT_HELP[kind]
        return Markup(value)

    @api.model
    def get_template_url(self, kind):
        """Backend download URL of the configured template, or False.

        Portal visitors go through /my/vendor-import-template/<kind>
        instead, which serves the file with sudo so an admin who forgets to
        tick 'public' on their own attachment does not break the portal.
        """
        attachment = self.get_template_attachment(kind)
        if not attachment:
            return False
        return '/web/content/%s?download=true' % attachment.id
