from odoo import api, fields, models
from odoo.exceptions import ValidationError


class InomFeeStructure(models.Model):
    """Per programme, per quota, per academic year.

    A structure is a template. Applying it to a student produces instalment
    lines and, where accounting is installed, an account.move. The structure
    itself never carries a balance — that lives on the student's fee account,
    so re-issuing a structure cannot silently rewrite what someone owes.
    """
    _name = 'inom.fee.structure'
    _description = 'Fee Structure'
    _inherit = ['inom.mixin']
    _order = 'year_id desc, programme_id'

    name = fields.Char(required=True, tracking=True)
    code = fields.Char(required=True, size=16)
    programme_id = fields.Many2one('inom.programme', required=True, index=True,
                                   ondelete='restrict', tracking=True)
    department_id = fields.Many2one(
        'inom.department', related='programme_id.department_id', store=True, index=True,
        ondelete='set null')
    year_id = fields.Many2one('inom.academic.year', required=True, index=True,
                              ondelete='restrict', tracking=True)
    semester = fields.Integer(default=1,
                              help='Zero applies the structure to the whole year.')
    quota = fields.Selection(
        [('general', 'General'), ('management', 'Management'),
         ('nri', 'NRI'), ('scholarship', 'Scholarship')],
        default='general', required=True, tracking=True)

    component_ids = fields.One2many('inom.fee.component', 'structure_id', string='Components')
    instalment_ids = fields.One2many('inom.fee.instalment', 'structure_id', string='Instalments')

    total_amount = fields.Monetary(compute='_compute_total', store=True, tracking=True)
    currency_id = fields.Many2one(
        'res.currency', default=lambda s: s.env.company.currency_id, required=True,
        ondelete='restrict')

    state = fields.Selection(
        [('draft', 'Draft'), ('published', 'Published'), ('closed', 'Closed')],
        default='draft', required=True, tracking=True)

    _code_uniq = models.Constraint(
        'UNIQUE(code, year_id, company_id)',
        'That fee structure code is already used for this academic year.')

    @api.depends('component_ids.amount')
    def _compute_total(self):
        for rec in self:
            rec.total_amount = sum(rec.component_ids.mapped('amount'))

    @api.constrains('instalment_ids', 'component_ids')
    def _check_instalments_add_up(self):
        """Instalment percentages must total 100.

        The prototype derived 40/35/25 on the fly. Real structures store them
        and they vary by programme, so this is the constraint that stops a
        university from billing 95% of a degree and finding out in March.
        """
        for rec in self:
            if not rec.instalment_ids:
                continue
            total = sum(rec.instalment_ids.mapped('percentage'))
            if abs(total - 100.0) > 0.01:
                raise ValidationError(
                    f'Instalments for {rec.name} add up to {total:.2f}%. They must total 100%.')

    def _inom_action_publish(self, payload=None):
        self.ensure_one()
        if not self.component_ids:
            raise ValidationError('Add at least one fee component before publishing.')
        self._check_instalments_add_up()
        self.write({'state': 'published'})
        return {'state': 'published'}

    def _inom_action_print(self, payload=None):
        """Hand back a URL rather than a PDF.

        Same shape as the fee receipt: the detail page follows `open_url`, so
        the document is rendered by the report controller, which checks the
        caller's own rights on the record before it renders anything.
        """
        self.ensure_one()
        return {'open_url': f'/ums/report/fee.structure/{self.id}'}

    @api.model
    def _inom_portal_fields(self):
        return ['id', 'display_name', 'name', 'code', 'programme_id', 'department_id',
                'year_id', 'semester', 'quota', 'total_amount', 'state', 'currency_id']


def _register_fee_structure_report():
    """Wire the fee structure sheet into the portal's report allow-list.

    The controller renders only what is registered here — the report key
    arrives from the client, and an unregistered key is a 404 rather than a
    render of whatever report happens to share the name.
    """
    from odoo.addons.inom_portal.controllers.report import register_report
    register_report(
        'fee.structure', 'inom_fee.action_report_fee_structure',
        'inom.fee.structure',
        lambda r: f'fee-structure-{(r.code or str(r.id)).replace("/", "-")}')


_register_fee_structure_report()


class InomFeeComponent(models.Model):
    """Tuition, examination, library, laboratory, hostel and the rest.

    Kept as lines rather than columns because every university has a different
    list, and a new head of fee should be a data entry, not a migration.
    """
    _name = 'inom.fee.component'
    _description = 'Fee Component'
    _order = 'structure_id, sequence, id'

    sequence = fields.Integer(default=10)
    structure_id = fields.Many2one(
        'inom.fee.structure', required=True, ondelete='cascade', index=True)
    name = fields.Char(required=True)
    code = fields.Char(size=16)
    amount = fields.Monetary(required=True)
    currency_id = fields.Many2one(related='structure_id.currency_id', store=True,
                                  ondelete='set null')
    refundable = fields.Boolean(default=False)
    optional = fields.Boolean(
        default=False, help='Charged only when the student opts in, e.g. transport.')
    account_id = fields.Many2one(
        'account.account', string='Income account', ondelete='set null',
        help='Left empty, the programme default is used when invoices are raised.')

    @api.constrains('amount')
    def _check_amount(self):
        for rec in self:
            if rec.amount < 0:
                raise ValidationError('A fee component cannot be negative. '
                                      'Use a scholarship or a waiver instead.')

    @api.model
    def _inom_portal_fields(self):
        return ['id', 'display_name', 'name', 'code', 'amount', 'refundable',
                'optional', 'structure_id',
                'account_id']


class InomFeeInstalment(models.Model):
    _name = 'inom.fee.instalment'
    _description = 'Fee Instalment'
    _order = 'structure_id, sequence, id'

    sequence = fields.Integer(default=10)
    structure_id = fields.Many2one(
        'inom.fee.structure', required=True, ondelete='cascade', index=True)
    name = fields.Char(required=True, help='For example: First instalment.')
    percentage = fields.Float(required=True, default=100.0)
    due_offset_days = fields.Integer(
        default=0, string='Due after (days)',
        help='Days after the academic year starts. Turned into a real date when '
             'the structure is applied to a student.')

    @api.constrains('percentage')
    def _check_percentage(self):
        for rec in self:
            if not 0 < rec.percentage <= 100:
                raise ValidationError('An instalment must be between 0 and 100 per cent.')

    @api.model
    def _inom_portal_fields(self):
        return ['id', 'display_name', 'name', 'percentage', 'due_offset_days', 'structure_id',
                'sequence']


class InomScholarship(models.Model):
    _name = 'inom.scholarship'
    _description = 'Scholarship / Waiver'
    _inherit = ['inom.mixin']
    _order = 'name'

    name = fields.Char(required=True, tracking=True)
    code = fields.Char(size=16)
    kind = fields.Selection(
        [('percent', 'Percentage of total'), ('amount', 'Fixed amount')],
        default='percent', required=True)
    value = fields.Float(required=True)
    funded_by = fields.Char(help='Government scheme, trust, or the university itself.')
    currency_id = fields.Many2one(
        'res.currency', default=lambda s: s.env.company.currency_id, required=True,
        ondelete='restrict')

    @api.constrains('kind', 'value')
    def _check_value(self):
        for rec in self:
            if rec.value <= 0:
                raise ValidationError('A scholarship must be worth something.')
            if rec.kind == 'percent' and rec.value > 100:
                raise ValidationError('A percentage scholarship cannot exceed 100%.')

    @api.model
    def _inom_portal_fields(self):
        return ['id', 'display_name', 'name', 'code', 'kind', 'value', 'funded_by']
