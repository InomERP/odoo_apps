# -*- coding: utf-8 -*-
from odoo import fields, models


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    is_wallet_journal = fields.Boolean(
        string='Wallet Journal',
        default=False,
        help='Technical flag identifying the journal used to track customer '
             'wallet balances.',
    )
