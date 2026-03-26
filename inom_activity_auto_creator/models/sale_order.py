from odoo import models, fields
from datetime import timedelta

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_confirm(self):
        res = super().action_confirm()

        # Use sudo to read rules
        rules = self.env['activity.rule'].sudo().search([
            ('model_id.model', '=', 'sale.order'),
            ('trigger', '=', 'confirm')
        ])

        model_id = self.env['ir.model']._get('sale.order').id
        picking_model_id = self.env['ir.model']._get('stock.picking').id  

        for order in self:
            for rule in rules:
                for user in rule.user_id:

                    # -------------------------
                    # 1. Sales Order Activity
                    # -------------------------
                    existing = self.env['mail.activity'].sudo().search([
                        ('res_id', '=', order.id),
                        ('res_model', '=', 'sale.order'),
                        ('summary', '=', rule.name),
                        ('user_id', '=', user.id),
                    ], limit=1)

                    if not existing:
                        self.env['mail.activity'].sudo().create({
                            'res_model_id': model_id,
                            'res_model': 'sale.order',
                            'res_id': order.id,
                            'activity_type_id': rule.activity_type_id.id,
                            'user_id': user.id,
                            'date_deadline': fields.Date.today() + timedelta(days=rule.days),
                            'summary': rule.name,
                            'note': rule.note,
                        })

                    
                    for picking in order.picking_ids:

                        existing_delivery = self.env['mail.activity'].sudo().search([
                            ('res_id', '=', picking.id),
                            ('res_model', '=', 'stock.picking'),
                            ('summary', '=', 'Prepare Delivery'),
                            ('user_id', '=', user.id),
                        ], limit=1)

                        if not existing_delivery:
                            self.env['mail.activity'].sudo().create({
                                'res_model_id': picking_model_id,
                                'res_model': 'stock.picking',
                                'res_id': picking.id,
                                'activity_type_id': rule.activity_type_id.id,
                                'user_id': user.id,
                                'date_deadline': fields.Date.today() + timedelta(days=rule.days),
                                'summary': 'Prepare Delivery',
                                'note': 'Prepare the delivery for this order',
                            })

        return res



# from odoo import models, fields
# from datetime import timedelta

# class SaleOrder(models.Model):
#     _inherit = 'sale.order'

#     def action_confirm(self):
#         res = super().action_confirm()

        
#         rules = self.env['activity.rule'].sudo().search([
#             ('model_id.model', '=', 'sale.order'),
#             ('trigger', '=', 'confirm')
#         ])

#         model_id = self.env['ir.model']._get('sale.order').id

#         for order in self:
#             for rule in rules:
#                 for user in rule.user_id:

                    
#                     existing = self.env['mail.activity'].sudo().search([
#                         ('res_id', '=', order.id),
#                         ('res_model', '=', 'sale.order'),
#                         ('summary', '=', rule.name),
#                         ('user_id', '=', user.id),
#                     ], limit=1)

#                     if not existing:
#                         self.env['mail.activity'].sudo().create({
#                             'res_model_id': model_id,
#                             'res_model': 'sale.order',
#                             'res_id': order.id,
#                             'activity_type_id': rule.activity_type_id.id,
#                             'user_id': user.id,
#                             'date_deadline': fields.Date.today() + timedelta(days=rule.days),
#                             'summary': rule.name,
#                             'note': rule.note,
#                         })

#         return res



