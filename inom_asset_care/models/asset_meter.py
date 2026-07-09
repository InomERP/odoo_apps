# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class InomAssetMeter(models.Model):
    _name = 'inom.asset.meter'
    _description = 'Asset Meter'

    name = fields.Char(string='Meter Name', required=True)
    asset_id = fields.Many2one(
        'inom.asset', string='Asset', required=True, ondelete='cascade')
    meter_type = fields.Selection([
        ('cumulative', 'Cumulative (Running Hours / Odometer)'),
        ('gauge', 'Gauge (Temperature / Pressure)'),
    ], string='Meter Type', default='cumulative', required=True)
    unit_label = fields.Char(string='Unit of Measure', default='Hours')
    reading_ids = fields.One2many(
        'inom.asset.meter.reading', 'meter_id', string='Readings')
    last_reading_value = fields.Float(
        string='Last Reading', compute='_compute_last_reading')
    last_reading_date = fields.Datetime(
        string='Last Reading On', compute='_compute_last_reading')
    warning_threshold = fields.Float(
        string='Warning Threshold',
        help='For gauge meters an activity is scheduled when a reading '
             'crosses this value.')
    company_id = fields.Many2one(
        related='asset_id.company_id', store=True)
    active = fields.Boolean(default=True)

    @api.depends('reading_ids.value', 'reading_ids.reading_datetime')
    def _compute_last_reading(self):
        for meter in self:
            last = meter.reading_ids.sorted(
                key=lambda r: r.reading_datetime, reverse=True)[:1]
            meter.last_reading_value = last.value if last else 0.0
            meter.last_reading_date = last.reading_datetime if last else False


class InomAssetMeterReading(models.Model):
    _name = 'inom.asset.meter.reading'
    _description = 'Asset Meter Reading'
    _order = 'reading_datetime desc, id desc'

    meter_id = fields.Many2one(
        'inom.asset.meter', string='Meter', required=True,
        ondelete='cascade')
    asset_id = fields.Many2one(
        related='meter_id.asset_id', store=True)
    value = fields.Float(string='Reading Value', required=True)
    reading_datetime = fields.Datetime(
        string='Reading Time', default=fields.Datetime.now, required=True)
    source = fields.Selection([
        ('manual', 'Manual Entry'),
        ('iot', 'IoT Device'),
    ], string='Source', default='manual', required=True)
    recorded_by_id = fields.Many2one(
        'res.users', string='Recorded By',
        default=lambda self: self.env.user)
    remarks = fields.Char(string='Remarks')

    @api.constrains('value')
    def _check_cumulative_progression(self):
        for reading in self:
            meter = reading.meter_id
            if meter.meter_type != 'cumulative':
                continue
            previous = self.search([
                ('meter_id', '=', meter.id),
                ('reading_datetime', '<', reading.reading_datetime),
            ], order='reading_datetime desc', limit=1)
            if previous and reading.value < previous.value:
                raise ValidationError(_(
                    'A cumulative meter reading cannot be lower than the '
                    'previous reading (%s).', previous.value))

    @api.model_create_multi
    def create(self, vals_list):
        readings = super().create(vals_list)
        for reading in readings:
            meter = reading.meter_id
            if meter.meter_type == 'gauge' and meter.warning_threshold \
                    and reading.value >= meter.warning_threshold:
                meter.asset_id.activity_schedule(
                    'mail.mail_activity_data_todo',
                    summary=_('Meter threshold crossed'),
                    note=_('Meter %s recorded %s %s which crosses the '
                           'warning threshold %s.',
                           meter.name, reading.value, meter.unit_label,
                           meter.warning_threshold),
                    user_id=self.env.ref('base.user_admin').id,
                )
            # Trigger meter based preventive plans
            self.env['inom.maintenance.plan'].sudo()._check_meter_trigger(
                meter)
        return readings
