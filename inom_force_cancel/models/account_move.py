# -*- coding: utf-8 -*-
from odoo import models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _inom_release_payment_links(self):
        """Break the reconciliation between these journal entries and any
        related payment so that the entries can later be reset to draft and
        cancelled without leaving dangling reconciliations behind."""
        for move in self:
            reconcilable_lines = move.line_ids.filtered(
                lambda line: line.account_id.reconcile)
            if reconcilable_lines:
                reconcilable_lines.remove_move_reconcile()

    def _inom_force_cancel(self):
        """Unreconcile, reset to draft and cancel the given customer
        invoices / credit notes."""
        for move in self.filtered(lambda m: m.state != 'cancel'):
            move._inom_release_payment_links()
            if move.state == 'posted':
                move.button_draft()
            move.button_cancel()
