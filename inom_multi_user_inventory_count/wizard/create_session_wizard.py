# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class StockInventoryCountSessionWizard(models.TransientModel):
    _name = 'stock.inventory.count.session.wizard'
    _description = 'Create Inventory Count Session'

    count_id = fields.Many2one(
        'stock.inventory.count',
        string='Inventory Count',
        required=True,
        ondelete='cascade',
    )
    user_ids = fields.Many2many(
        'res.users',
        string='Users',
        help='One counting session is created for each selected user.',
    )
    product_ids = fields.Many2many(
        'product.product',
        string='Products',
        compute='_compute_product_ids',
        help='Products carried over from the inventory count (read-only).',
    )

    @api.depends('count_id')
    def _compute_product_ids(self):
        for wizard in self:
            wizard.product_ids = wizard.count_id.product_line_ids.product_id

    def _prepare_session_line_dicts(self):
        self.ensure_one()
        count = self.count_id
        location_obj = self.env['stock.location']
        base_location = count.location_id or count.warehouse_id.view_location_id
        locations = location_obj.search([
            ('id', 'child_of', base_location.id),
            ('usage', '=', 'internal'),
        ])
        line_dicts = []
        for product_line in count.product_line_ids:
            for location in locations:
                line_dicts.append({
                    'product_id': product_line.product_id.id,
                    'location_id': location.id,
                })
        return line_dicts

    def _send_session_assignment_email(self, session):
        """Send assignment email with direct session link."""
        if not session.user_id or not session.user_id.email:
            return

        # Base URL get karo
        base_url = self.env['ir.config_parameter'].sudo().get_param(
            'web.base.url', 'http://localhost:8069'
        )

        location_name = (
            session.location_id.complete_name
            if session.location_id
            else 'All Locations'
        )

        # Direct session link
        session_url = '%s/odoo/inventory-sessions/%d' % (
            base_url, session.id)

        body = """
<div style="font-family: Arial, sans-serif; font-size: 14px;
            color: #333; max-width: 600px; margin: 0 auto;">

    <div style="background-color: #6c2fa0; padding: 20px;
                border-radius: 6px 6px 0 0; text-align: center;">
        <h2 style="color: white; margin: 0;">
            New Inventory Session Assigned
        </h2>
    </div>

    <div style="padding: 25px; background-color: #f9f9f9;
                border: 1px solid #e0e0e0;">

        <p>Dear <strong>%(user_name)s</strong>,</p>

        <p>A new inventory counting session has been assigned to you.
           Please find the details below:</p>

        <div style="background-color: white;
                    border-left: 4px solid #6c2fa0;
                    padding: 15px; margin: 15px 0;
                    border-radius: 4px;">
            <table style="border-collapse: collapse; width: 100%%;">
                <tr>
                    <td style="padding: 6px 20px 6px 0; color: #888;
                               width: 40%%;">Session Reference</td>
                    <td style="padding: 6px 0;
                               font-weight: bold;">%(session_name)s</td>
                </tr>
                <tr>
                    <td style="padding: 6px 20px 6px 0;
                               color: #888;">Inventory Count</td>
                    <td style="padding: 6px 0;">%(count_name)s</td>
                </tr>
                <tr>
                    <td style="padding: 6px 20px 6px 0;
                               color: #888;">Warehouse</td>
                    <td style="padding: 6px 0;">%(warehouse)s</td>
                </tr>
                <tr>
                    <td style="padding: 6px 20px 6px 0;
                               color: #888;">Location</td>
                    <td style="padding: 6px 0;">%(location)s</td>
                </tr>
                <tr>
                    <td style="padding: 6px 20px 6px 0;
                               color: #888;">Approver</td>
                    <td style="padding: 6px 0;">%(approver)s</td>
                </tr>
            </table>
        </div>

        <div style="text-align: center; margin: 25px 0;">
            <a href="%(session_url)s"
               style="background-color: #6c2fa0;
                      color: white;
                      padding: 14px 35px;
                      text-decoration: none;
                      border-radius: 5px;
                      font-size: 16px;
                      font-weight: bold;
                      display: inline-block;">
                Start Counting Now
            </a>
        </div>

        <p style="font-size: 12px; color: #888; text-align: center;">
            If the button does not work, copy and paste this link
            in your browser:<br/>
            <a href="%(session_url)s"
               style="color: #6c2fa0;">%(session_url)s</a>
        </p>

        <p>Regards,<br/><strong>%(company)s</strong></p>

    </div>

    <div style="background-color: #f0f0f0; padding: 12px;
                text-align: center;
                border-radius: 0 0 6px 6px;
                border: 1px solid #e0e0e0;
                border-top: none;">
        <p style="margin: 0; font-size: 11px; color: #999;">
            This is an automated message from
            InomERP Inventory Count Module.
        </p>
    </div>

</div>
""" % {
            'user_name': session.user_id.name,
            'session_name': session.name,
            'count_name': session.inventory_count_id.name,
            'warehouse': session.warehouse_id.name,
            'location': location_name,
            'approver': session.approver_id.name,
            'session_url': session_url,
            'company': session.company_id.name,
        }

        mail_vals = {
            'subject': 'Inventory Counting Session Assigned — %s' % (
                session.name),
            'email_to': session.user_id.email,
            'email_from': (
                self.env.company.email or self.env.user.email),
            'body_html': body,
            'auto_delete': True,
        }
        mail = self.env['mail.mail'].sudo().create(mail_vals)
        mail.sudo().send()

    def action_create_sessions(self):
        self.ensure_one()
        count = self.count_id
        if not count.product_line_ids:
            raise UserError(_(
                "Please add at least one product to the inventory count "
                "before creating sessions."))
        if not self.user_ids:
            raise UserError(_(
                "Please select at least one user to assign the session."))

        session_obj = self.env['stock.inventory.count.session']
        line_dicts = self._prepare_session_line_dicts()
        sessions = session_obj.browse()
        for user in self.user_ids:
            sessions |= session_obj.create({
                'inventory_count_id': count.id,
                'user_id': user.id,
                'warehouse_id': count.warehouse_id.id,
                'location_id': count.location_id.id,
                'use_barcode_scanner': count.use_barcode_scanner,
                'session_type': count.session_type,
                'session_line_ids': [
                    (0, 0, dict(values)) for values in line_dicts
                ],
            })

        if count.state == 'draft':
            count.state = 'in_progress'

        # Send assignment email to each assigned user
        for session in sessions:
            self._send_session_assignment_email(session)

        action = self.env['ir.actions.actions']._for_xml_id(
            'inom_multi_user_inventory_count'
            '.action_stock_inventory_count_session')
        if len(sessions) == 1:
            action.update({
                'view_mode': 'form',
                'views': [(False, 'form')],
                'res_id': sessions.id,
            })
        else:
            action['domain'] = [('id', 'in', sessions.ids)]
        return action
