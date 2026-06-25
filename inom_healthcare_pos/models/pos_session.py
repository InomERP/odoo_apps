from odoo import models, fields, api, _
from odoo.exceptions import UserError


class HealthcarePosSession(models.Model):
    """A cashier's working period on a terminal. Mirrors the Odoo POS session
    lifecycle (opening control -> opened -> closing control -> closed) and
    tracks opening/closing cash so each branch reconciles independently."""

    _name = 'healthcare.pos.session'
    _description = 'Healthcare POS Session'
    _order = 'id desc'
    _inherit = ['mail.thread']

    name = fields.Char(default='/', readonly=True, copy=False)
    config_id = fields.Many2one(
        'healthcare.pos.config', string='Point of Sale',
        required=True, ondelete='cascade', index=True)
    user_id = fields.Many2one(
        'res.users', string='Cashier', required=True,
        default=lambda self: self.env.user)
    company_id = fields.Many2one(
        'res.company', related='config_id.company_id', store=True, readonly=True)
    currency_id = fields.Many2one(
        'res.currency', related='config_id.currency_id', store=True, readonly=True)

    state = fields.Selection([
        ('opening_control', 'Opening Control'),
        ('opened', 'In Progress'),
        ('closing_control', 'Closing Control'),
        ('closed', 'Closed'),
    ], default='opening_control', tracking=True, copy=False)

    start_at = fields.Datetime(string='Opened On', readonly=True)
    stop_at = fields.Datetime(string='Closed On', readonly=True)

    opening_balance = fields.Float(string='Opening Cash')
    closing_balance = fields.Float(string='Closing Cash')
    theoretical_cash = fields.Float(
        string='Theoretical Cash', compute='_compute_totals', store=True)
    cash_difference = fields.Float(
        string='Difference', compute='_compute_cash_difference', store=True)

    order_ids = fields.One2many('healthcare.pos.order', 'session_id', string='Orders')
    order_count = fields.Integer(compute='_compute_totals', store=True)
    total_sales = fields.Float(compute='_compute_totals', store=True)
    cash_sales = fields.Float(compute='_compute_totals', store=True)

    @api.depends('order_ids', 'order_ids.state', 'order_ids.amount_total',
                 'order_ids.payment_ids.amount', 'order_ids.payment_ids.is_cash',
                 'opening_balance')
    def _compute_totals(self):
        for rec in self:
            paid_orders = rec.order_ids.filtered(lambda o: o.state in ('paid', 'done', 'invoiced'))
            rec.order_count = len(paid_orders)
            rec.total_sales = sum(paid_orders.mapped('amount_total'))
            cash = 0.0
            for order in paid_orders:
                cash += sum(order.payment_ids.filtered('is_cash').mapped('amount'))
            rec.cash_sales = cash
            rec.theoretical_cash = (rec.opening_balance or 0.0) + cash

    @api.depends('closing_balance', 'theoretical_cash')
    def _compute_cash_difference(self):
        for rec in self:
            rec.cash_difference = (rec.closing_balance or 0.0) - (rec.theoretical_cash or 0.0)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', '/') in ('/', False):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'healthcare.pos.session') or '/'
        sessions = super().create(vals_list)
        for session in sessions:
            if not session.config_id.set_opening_balance:
                session.action_open_session()
        return sessions

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def action_open_session(self):
        for rec in self:
            rec.write({'state': 'opened', 'start_at': fields.Datetime.now()})
        return True

    def action_set_closing_control(self):
        self.write({'state': 'closing_control'})

    def action_close_session(self):
        for rec in self:
            if rec.order_ids.filtered(lambda o: o.state == 'draft'):
                raise UserError(_(
                    "You cannot close a session with unpaid (draft) orders. "
                    "Settle or cancel them first."))
            rec.write({'state': 'closed', 'stop_at': fields.Datetime.now()})
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'healthcare.pos.session',
            'res_id': self.id,
            'view_mode': 'form',
            'views': [(False, 'form')],
            'target': 'current',
        }

    def action_open_ui(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.client',
            'tag': 'inom_healthcare_pos.app',
            'params': {'config_id': self.config_id.id},
        }

    def action_view_orders(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Orders'),
            'res_model': 'healthcare.pos.order',
            'view_mode': 'list,form',
            'views': [(False, 'list'), (False, 'form')],
            'domain': [('session_id', '=', self.id)],
            'context': {'default_session_id': self.id},
        }

    # ------------------------------------------------------------------
    # Frontend helpers (called from the OWL app)
    # ------------------------------------------------------------------
    def _session_ui_data(self):
        self.ensure_one()
        return {
            'id': self.id,
            'name': self.name,
            'state': self.state,
            'user': self.user_id.name,
            'opening_balance': self.opening_balance,
            'start_at': self.start_at and fields.Datetime.to_string(self.start_at) or '',
            'order_count': self.order_count,
            'total_sales': self.total_sales,
        }

    @api.model
    def open_session_from_ui(self, config_id, opening_balance=0.0):
        """Create/resume a session for the current user on a config and return
        its UI payload. Called by the OWL opening-control screen."""
        config = self.env['healthcare.pos.config'].browse(config_id).exists()
        if not config:
            raise UserError(_("Unknown Point of Sale configuration."))
        session = self.search([
            ('config_id', '=', config_id),
            ('user_id', '=', self.env.user.id),
            ('state', 'in', ('opening_control', 'opened')),
        ], limit=1)
        if not session:
            session = self.create({
                'config_id': config_id,
                'user_id': self.env.user.id,
                'opening_balance': opening_balance,
            })
        else:
            session.opening_balance = opening_balance
        session.action_open_session()
        return session._session_ui_data()

    def close_session_from_ui(self, closing_balance=0.0):
        """Set closing cash and close the session. Returns a small report."""
        self.ensure_one()
        self.closing_balance = closing_balance
        self.action_set_closing_control()
        self.action_close_session()
        return {
            'id': self.id,
            'name': self.name,
            'opening_balance': self.opening_balance,
            'cash_sales': self.cash_sales,
            'theoretical_cash': self.theoretical_cash,
            'closing_balance': self.closing_balance,
            'cash_difference': self.cash_difference,
            'total_sales': self.total_sales,
            'order_count': self.order_count,
        }
