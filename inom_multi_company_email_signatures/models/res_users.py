# -*- coding: utf-8 -*-

from odoo import api, models, fields


class ResUsers(models.Model):
    _inherit = 'res.users'

    signature_ids = fields.One2many(
        comodel_name='res.users.signature',
        inverse_name='user_id',
        string='Company Signatures',
    )

    signature = fields.Html(
        compute='_compute_signature',
        inverse='_inverse_signature',
        store=False,
        readonly=False,
        override=True,
    )

    @api.depends('signature_ids', 'signature_ids.signature', 'company_id')
    def _compute_signature(self):
        for user in self:
            if not user.id:
                user.signature = False
                continue

            # Use env.company (active company in session) if it matches
            # user's companies, otherwise fall back to user.company_id
            active_company = self.env.company
            if active_company in user.company_ids:
                company = active_company
            else:
                company = user.company_id

            rec = user.signature_ids.filtered(
                lambda s: s.company_id == company
            )
            if len(rec) > 1:
                rec = rec[0]

            if not rec or not rec.signature:
                user.signature = False
                continue

            raw = rec.signature

            if raw.startswith('draw:'):
                src = raw[5:]
            elif raw.startswith('typed:'):
                src = raw[6:]
            elif raw.startswith('upload:'):
                src = raw[7:]
            else:
                src = raw

            if src.startswith('data:image'):
                user.signature = (
                        '<img src="%s" '
                        'style="max-height:80px; max-width:300px;" '
                        'alt="signature"/>' % src
                )
            else:
                user.signature = src

    def _inverse_signature(self):
        Sig = self.env['res.users.signature'].sudo()
        for user in self:
            if not user.id:
                continue
            user_sudo = user.sudo()
            company_id = (user_sudo.company_id or self.env.company).id
            if not company_id:
                continue
            sig_value = user.signature
            if not sig_value:
                continue
            rec = Sig.search([
                ('user_id',    '=', user.id),
                ('company_id', '=', company_id),
            ], limit=1)
            if rec:
                rec.write({'signature': sig_value})
            else:
                Sig.create({
                    'user_id':    user.id,
                    'company_id': company_id,
                    'signature':  sig_value,
                })

    def write(self, vals):
        if vals.get('signature_ids') and len(self) == 1:
            Sig = self.env['res.users.signature'].sudo()
            new_commands = []
            for command in vals['signature_ids']:
                if command[0] == 0:
                    cvals = command[2] or {}
                    company_id = cvals.get('company_id') or self.env.company.id
                    sig_value  = cvals.get('signature')
                    if not sig_value:
                        continue
                    old = Sig.search([
                        ('user_id',    '=', self.id),
                        ('company_id', '=', company_id),
                    ])
                    if old:
                        old.unlink()
                    new_commands.append(command)
                else:
                    new_commands.append(command)
            vals = dict(vals)
            vals['signature_ids'] = new_commands

        return super(ResUsers, self.sudo()).write(vals)