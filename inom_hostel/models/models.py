from odoo import api, fields, models
from odoo.exceptions import ValidationError


class InomHostelBlock(models.Model):
    _name = 'inom.hostel.block'
    _description = 'Hostel Block'
    _inherit = ['inom.mixin']
    _order = 'name'

    name = fields.Char(required=True, tracking=True)
    code = fields.Char(required=True, size=8)
    block_for = fields.Selection(
        [('women', "Women's"), ('men', "Men's"), ('mixed', 'Mixed')],
        default='mixed', required=True)
    warden_id = fields.Many2one('res.users', string='Resident warden')
    floors = fields.Integer(default=3)
    room_ids = fields.One2many('inom.hostel.room', 'block_id', string='Rooms')

    rooms_total = fields.Integer(compute='_compute_occupancy', store=True)
    beds_total = fields.Integer(compute='_compute_occupancy', store=True)
    beds_taken = fields.Integer(compute='_compute_occupancy', store=True)
    occupancy = fields.Float(compute='_compute_occupancy', store=True,
                             string='Occupancy (%)')

    _code_uniq = models.Constraint(
        'UNIQUE(code, company_id)',
        'That block code is already in use.')

    @api.depends('room_ids.capacity', 'room_ids.occupied')
    def _compute_occupancy(self):
        for rec in self:
            rec.rooms_total = len(rec.room_ids)
            rec.beds_total = sum(rec.room_ids.mapped('capacity'))
            rec.beds_taken = sum(rec.room_ids.mapped('occupied'))
            rec.occupancy = (rec.beds_taken / rec.beds_total * 100.0) if rec.beds_total else 0.0

    @api.model
    def _inom_portal_fields(self):
        return ['id', 'display_name', 'name', 'code', 'block_for', 'warden_id',
                'floors', 'rooms_total', 'beds_total', 'beds_taken', 'occupancy']


class InomHostelRoom(models.Model):
    _name = 'inom.hostel.room'
    _description = 'Hostel Room'
    _inherit = ['inom.mixin']
    _order = 'block_id, number'
    _rec_name = 'display_name'
    _rec_names_search = ['number', 'block_id.code', 'block_id.name']

    block_id = fields.Many2one('inom.hostel.block', required=True,
                               ondelete='cascade', index=True)
    number = fields.Char(required=True)
    floor = fields.Integer(default=0)
    capacity = fields.Integer(required=True, default=2)
    room_type = fields.Selection(
        [('single', 'Single'), ('double', 'Double'), ('triple', 'Triple'),
         ('dorm', 'Dormitory')],
        default='double', required=True)
    has_ac = fields.Boolean(string='Air conditioned')
    monthly_rent = fields.Monetary()
    currency_id = fields.Many2one(
        'res.currency', default=lambda s: s.env.company.currency_id, required=True)

    allocation_ids = fields.One2many('inom.hostel.allocation', 'room_id',
                                     string='Allocations')
    # Computed from active allocations, never a stored counter that someone
    # increments by hand. A counter drifts the first time an allocation is
    # archived out of order, and the warden finds out when two students arrive
    # at the same bed.
    occupied = fields.Integer(compute='_compute_occupied', store=True)
    beds_free = fields.Integer(compute='_compute_occupied', store=True)
    state = fields.Selection(
        [('available', 'Available'), ('partial', 'Partly filled'),
         ('full', 'Full'), ('maintenance', 'Maintenance')],
        compute='_compute_occupied', store=True, index=True)

    maintenance = fields.Boolean(
        default=False, help='Takes the room out of allocation without deleting it.')

    _room_uniq = models.Constraint(
        'UNIQUE(block_id, number)',
        'That room number already exists in the block.')

    @api.depends('allocation_ids.state', 'capacity', 'maintenance')
    def _compute_occupied(self):
        for rec in self:
            rec.occupied = len(rec.allocation_ids.filtered(lambda a: a.state == 'active'))
            rec.beds_free = max(0, rec.capacity - rec.occupied)
            if rec.maintenance:
                rec.state = 'maintenance'
            elif rec.occupied >= rec.capacity:
                rec.state = 'full'
            elif rec.occupied:
                rec.state = 'partial'
            else:
                rec.state = 'available'

    @api.depends('block_id.code', 'number')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = f'{rec.block_id.code}-{rec.number}'

    @api.model
    def _inom_portal_fields(self):
        return ['id', 'display_name', 'block_id', 'number', 'floor', 'capacity',
                'room_type', 'has_ac', 'monthly_rent', 'occupied', 'beds_free',
                'state', 'maintenance', 'currency_id']


class InomHostelAllocation(models.Model):
    _name = 'inom.hostel.allocation'
    _description = 'Hostel Allocation'
    _inherit = ['inom.mixin']
    _order = 'date_from desc'
    _rec_name = 'display_name'
    _rec_names_search = ['student_id.name', 'student_id.enrolment_no',
                         'room_id.number', 'block_id.code']

    student_id = fields.Many2one('inom.student', required=True, index=True)
    room_id = fields.Many2one('inom.hostel.room', required=True, index=True)
    block_id = fields.Many2one(related='room_id.block_id', store=True, index=True)
    department_id = fields.Many2one(
        'inom.department', related='student_id.department_id', store=True, index=True)
    year_id = fields.Many2one('inom.academic.year', required=True, index=True)

    date_from = fields.Date(required=True, default=fields.Date.context_today)
    date_to = fields.Date()
    state = fields.Selection(
        [('active', 'Resident'), ('vacated', 'Vacated'), ('cancelled', 'Cancelled')],
        default='active', required=True, index=True, tracking=True)

    @api.constrains('room_id', 'state')
    def _check_capacity(self):
        """Refuse to over-allocate a room.

        Checked here rather than reported on a dashboard: the cost of finding
        out later is a student arriving with luggage and nowhere to sleep.
        """
        for rec in self.filtered(lambda a: a.state == 'active'):
            if rec.room_id.maintenance:
                raise ValidationError(
                    f'Room {rec.room_id.display_name} is under maintenance.')
            residents = self.search_count([
                ('room_id', '=', rec.room_id.id), ('state', '=', 'active'),
            ])
            if residents > rec.room_id.capacity:
                raise ValidationError(
                    f'Room {rec.room_id.display_name} holds {rec.room_id.capacity}. '
                    f'It is already full.')

    @api.constrains('student_id', 'state')
    def _check_one_room(self):
        for rec in self.filtered(lambda a: a.state == 'active'):
            others = self.search_count([
                ('id', '!=', rec.id), ('student_id', '=', rec.student_id.id),
                ('state', '=', 'active'),
            ])
            if others:
                raise ValidationError(
                    f'{rec.student_id.name} already has a room. Vacate it first.')

    @api.depends('student_id.name', 'room_id.display_name')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = f'{rec.student_id.name} · {rec.room_id.display_name}'

    def _inom_action_vacate(self, payload=None):
        self.ensure_one()
        if self.state != 'active':
            raise ValidationError('This allocation is not active.')
        self.write({'state': 'vacated', 'date_to': fields.Date.context_today(self)})
        return {'state': 'vacated'}

    @api.model
    def _inom_portal_fields(self):
        return ['id', 'display_name', 'student_id', 'room_id', 'block_id',
                'year_id', 'date_from', 'date_to', 'state']


class InomHostelVisitor(models.Model):
    _name = 'inom.hostel.visitor'
    _description = 'Visitor Register'
    _inherit = ['inom.mixin']
    _order = 'checked_in desc'

    name = fields.Char(string='Visitor', required=True)
    student_id = fields.Many2one('inom.student', string='Visiting', required=True, index=True)
    block_id = fields.Many2one('inom.hostel.block', required=True, index=True)
    relation = fields.Char()
    phone = fields.Char(required=True)
    checked_in = fields.Datetime(required=True, default=fields.Datetime.now)
    checked_out = fields.Datetime()
    purpose = fields.Char()

    @api.constrains('checked_in', 'checked_out')
    def _check_times(self):
        for rec in self:
            if rec.checked_out and rec.checked_out < rec.checked_in:
                raise ValidationError('A visitor cannot leave before they arrive.')

    def _inom_action_check_out(self, payload=None):
        self.ensure_one()
        if self.checked_out:
            raise ValidationError('This visitor has already signed out.')
        self.checked_out = fields.Datetime.now()
        return {'checked_out': True}

    @api.model
    def _inom_portal_fields(self):
        return ['id', 'display_name', 'name', 'student_id', 'block_id', 'relation',
                'phone', 'checked_in', 'checked_out', 'purpose']
