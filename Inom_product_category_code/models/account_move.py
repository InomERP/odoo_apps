from odoo import models, _
from odoo.exceptions import UserError

class AccountMove(models.Model):
    _inherit = 'account.move'

    def action_post(self):
        for move in self:
            if move.move_type == 'out_invoice' and not move.ref:
                raise UserError(
                    _('Customer Reference is required before posting the invoice.')
                )
        return super().action_post()


    def unlink(self):
        for move in self:
            if move.move_type=='out_invoice' and move.state=='posted':
                raise UserError(

                    "You cannot delete a posted Customer Invoice"
                     

                    )   
        
        return super().unlink()


                