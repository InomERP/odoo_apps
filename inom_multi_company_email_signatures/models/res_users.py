# -*- coding: utf-8 -*-

from odoo import api, models, fields
from odoo.fields import Command


class ResUsers(models.Model):
    _inherit = 'res.users'

    signature_ids = fields.One2many(
        comodel_name='res.users.signature',
        inverse_name='user_id',
        string='Company Signatures',
        user_writeable=True,
    )

    signature = fields.Html(
        compute='_compute_signature',
        inverse='_inverse_signature',
        store=False,
        readonly=False,
        user_writeable=True,
    )

    def _get_signature_company(self):
        """Company whose signature applies to this user.

        Use env.company (active company in session) if it matches the user's
        companies, otherwise fall back to user.company_id.
        """
        self.ensure_one()
        active_company = self.env.company
        if active_company in self.company_ids:
            return active_company
        return self.company_id

    @api.depends('signature_ids', 'signature_ids.signature', 'company_id')
    def _compute_signature(self):
        for user in self:
            if not user.id:
                user.signature = False
                continue

            company = user._get_signature_company()
            rec = user.signature_ids.filtered(
                lambda s: s.company_id == company
            )[:1]

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
        users = self.filtered('id')
        if not users:
            return
        # sudo: the inverse only runs inside res.users.write(), which has
        # already checked that the caller may edit these users; this also lets
        # user managers maintain signatures of other users.
        Sig = self.env['res.users.signature'].sudo()
        existing = {
            (sig.user_id.id, sig.company_id.id): sig
            for sig in Sig.search([('user_id', 'in', users.ids)])
        }
        vals_list = []
        for user in users:
            company = user._get_signature_company()
            sig_value = user.signature
            if not company or not sig_value:
                continue
            rec = existing.get((user.id, company.id))
            if rec:
                # cache assignment: flushed together with the other updates
                rec.signature = sig_value
            else:
                vals_list.append({
                    'user_id':    user.id,
                    'company_id': company.id,
                    'signature':  sig_value,
                })
        if vals_list:
            Sig.create(vals_list)

    def write(self, vals):
        if vals.get('signature_ids') and len(self) == 1:
            # Fail before removing anything if the caller may not edit this user
            self.check_access('write')
            new_commands = []
            replaced_company_ids = set()
            for command in vals['signature_ids']:
                if command[0] == Command.CREATE:
                    cvals = command[2] or {}
                    if not cvals.get('signature'):
                        continue
                    replaced_company_ids.add(
                        cvals.get('company_id') or self.env.company.id
                    )
                new_commands.append(command)
            if replaced_company_ids:
                # sudo: access to this user was checked above; the previous
                # signature of a company is replaced by the newly created one.
                self.env['res.users.signature'].sudo().search([
                    ('user_id',    '=',  self.id),
                    ('company_id', 'in', list(replaced_company_ids)),
                ]).unlink()
            vals = dict(vals, signature_ids=new_commands)

        return super().write(vals)
