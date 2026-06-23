# -*- coding: utf-8 -*-
from odoo import models, fields, _


class MaterialRequisitionRejectWizard(models.TransientModel):
    _name = 'material.requisition.reject.wizard'
    _description = 'Rejection Reason Wizard'

    requisition_id = fields.Many2one(
        'material.requisition',
        string='Requisition',
        required=True,
    )
    rejection_reason = fields.Text(
        string='Reason For Rejection',
        required=True,
    )
    reject_type = fields.Selection([
        ('manager', 'Manager'),
        ('user', 'User'),
    ], string='Reject Type', required=True)

    def action_confirm_reject(self):
        self.ensure_one()
        requisition = self.requisition_id
        requisition.write({
            'state': 'rejected',
            'rejection_reason': self.rejection_reason,
        })
        # Chatter message + email
        requisition.message_post(
            body=_("Requisition rejected by %s.\n\nReason: %s") % (
                self.env.user.name, self.rejection_reason
            ),
            subject=_("Rejected: %s") % requisition.name,
            message_type='email',
            subtype_xmlid='mail.mt_comment',
        )
        return {'type': 'ir.actions.act_window_close'}