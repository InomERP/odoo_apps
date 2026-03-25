from odoo import models, fields
from datetime import timedelta

class AccountMove(models.Model):
    _inherit = 'account.move'

    def action_post(self):
        res = super().action_post()

        # Read rules with admin rights
        rules = self.env['activity.rule'].sudo().search([
            ('model_id.model', '=', 'account.move'),
            ('trigger', '=', 'post')
        ])

        model_id = self.env['ir.model']._get('account.move').id

        for move in self:
            for rule in rules:
                for user in rule.user_id:

                    # Prevent duplicate activities
                    existing = self.env['mail.activity'].sudo().search([
                        ('res_id', '=', move.id),
                        ('res_model', '=', 'account.move'),
                        ('activity_type_id', '=', rule.activity_type_id.id),
                        ('user_id', '=', user.id),
                    ], limit=1)

                    if move.id and not existing:
                        self.env['mail.activity'].sudo().create({
                            'res_model_id': model_id,
                            'res_model': 'account.move',
                            'res_id': move.id,
                            'activity_type_id': rule.activity_type_id.id,
                            'user_id': user.id,
                            'date_deadline': fields.Date.today() + timedelta(days=rule.days),
                            'summary': rule.name,
                            'note': rule.note,
                        })

        return res



# from odoo import models, fields
# from datetime import timedelta

# class AccountMove(models.Model):
#     _inherit = 'account.move'

#     def action_post(self):

#         res = super().action_post()

#         rules = self.env['activity.rule'].search([
#             ('model_id.model', '=', 'account.move'),
#             ('trigger', '=', 'post')
#         ])

#         model_id = self.env['ir.model']._get('account.move').id

#         for move in self:

#             for rule in rules:

#                 for user in rule.user_id:

#                     existing = self.env['mail.activity'].search([
#                         ('res_id','=',move.id),
#                         ('res_model','=','account.move'),
#                         ('activity_type_id','=',rule.activity_type_id.id),
#                         ('user_id','=',user.id),
#                     ],limit=1)

#                     if move.id and not existing:

#                         self.env['mail.activity'].create({

#                             'res_model_id': model_id,
#                             'res_model': 'account.move',
#                             'res_id': move.id,

#                             'activity_type_id': rule.activity_type_id.id,

#                             'user_id': user.id,

#                             'date_deadline': fields.Date.today() + timedelta(days=rule.days),
#                             'summary': rule.name,

#                             'note': rule.note,
#                         })

#         return res

# from odoo import models, fields
# from datetime import timedelta

# class AccountMove(models.Model):
#     _inherit = 'account.move'

#     def action_post(self):
#         res = super().action_post()

#         rules = self.env['activity.rule'].search([
#             ('model_id.model', '=', 'account.move'),
#             ('trigger', '=', 'post')
#         ])

#         for move in self:
#             for rule in rules:
#                 for user in rule.user_id: 
#                     self.env['mail.activity'].create({
#                         'res_model_id': self.env['ir.model']._get(move._name).id,
#                         'res_id': move.id,
#                         'activity_type_id': rule.activity_type_id.id,
#                         'user_id': user.id,  
#                         'date_deadline': fields.Date.today() + timedelta(days=rule.days),
#                         'summary': rule.name,
#                         'note': rule.note,
#                     })

#         return res
