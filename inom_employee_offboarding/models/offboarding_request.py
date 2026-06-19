# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class InomOffboardingRequest(models.Model):
    _name = 'inom.offboarding.request'
    _description = 'Employee Offboarding Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'request_date desc, id desc'

    name = fields.Char(
        string='Reference',
        required=True,
        copy=False,
        readonly=True,
        index=True,
        default=lambda self: _('New'),
    )
    employee_id = fields.Many2one(
        comodel_name='hr.employee',
        string='Employee',
        required=True,
        tracking=True,
        states={'draft': [('readonly', False)]},
    )
    department_id = fields.Many2one(
        comodel_name='hr.department',
        string='Department',
        compute='_compute_employee_details',
        store=True,
        readonly=True,
    )
    job_id = fields.Many2one(
        comodel_name='hr.job',
        string='Job Position',
        compute='_compute_employee_details',
        store=True,
        readonly=True,
    )
    manager_id = fields.Many2one(
        comodel_name='hr.employee',
        string='Reporting Manager',
        compute='_compute_employee_details',
        store=True,
        readonly=True,
    )
    offboarding_type = fields.Selection(
        selection=[
            ('resignation', 'Resignation'),
            ('retirement', 'Retirement'),
            ('termination', 'Termination'),
            ('contract_end', 'End of Contract'),
        ],
        string='Offboarding Type',
        default='resignation',
        required=True,
        tracking=True,
    )
    reason_id = fields.Many2one(
        comodel_name='inom.offboarding.reason',
        string='Offboarding Reason',
        tracking=True,
    )
    request_date = fields.Date(
        string='Request Date',
        default=fields.Date.context_today,
        required=True,
        tracking=True,
    )
    proposed_last_day = fields.Date(
        string='Proposed Last Working Day',
        tracking=True,
        help='Last working day proposed by the employee.',
    )
    notice_period_days = fields.Integer(
        string='Notice Period (Days)',
        tracking=True,
        help='Notice period decided by HR during the process.',
    )
    relieving_date = fields.Date(
        string='Relieving Date',
        tracking=True,
        help='Final relieving date confirmed by HR.',
    )
    employee_remarks = fields.Text(string='Employee Remarks')
    hr_remarks = fields.Text(string='HR Remarks')
    rejection_reason = fields.Text(
        string='Rejection Reason',
        readonly=True,
        copy=False,
    )
    checklist_line_ids = fields.One2many(
        comodel_name='inom.offboarding.checklist.line',
        inverse_name='request_id',
        string='Clearance Checklist',
    )
    checklist_progress = fields.Float(
        string='Checklist Progress',
        compute='_compute_checklist_progress',
        store=True,
    )
    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('manager_approval', 'Manager Approval'),
            ('hr_approval', 'HR Approval'),
            ('approved', 'Approved'),
            ('relieved', 'Relieved'),
            ('rejected', 'Rejected'),
            ('cancelled', 'Cancelled'),
        ],
        string='Status',
        default='draft',
        tracking=True,
        copy=False,
    )
    active = fields.Boolean(string='Active', default=True)
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company',
        default=lambda self: self.env.company,
    )
    access_url = fields.Char(
        string='Record URL',
        compute='_compute_access_url',
    )

    # ------------------------------------------------------------------
    # Compute methods
    # ------------------------------------------------------------------
    def _compute_access_url(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        for record in self:
            if record.id and base_url:
                record.access_url = (
                    '%s/web#id=%s&model=inom.offboarding.request&view_type=form'
                    % (base_url, record.id)
                )
            else:
                record.access_url = False
    @api.depends('employee_id')
    def _compute_employee_details(self):
        for record in self:
            employee = record.employee_id
            record.department_id = employee.department_id
            record.job_id = employee.job_id
            record.manager_id = employee.parent_id

    @api.depends('checklist_line_ids', 'checklist_line_ids.is_done')
    def _compute_checklist_progress(self):
        for record in self:
            lines = record.checklist_line_ids
            total = len(lines)
            done = len(lines.filtered('is_done'))
            record.checklist_progress = (done / total * 100.0) if total else 0.0

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------
    @api.constrains('proposed_last_day', 'request_date')
    def _check_dates(self):
        for record in self:
            if (record.proposed_last_day and record.request_date
                    and record.proposed_last_day < record.request_date):
                raise ValidationError(_(
                    'The proposed last working day cannot be earlier '
                    'than the request date.'))

    @api.constrains('notice_period_days')
    def _check_notice_period(self):
        for record in self:
            if record.notice_period_days < 0:
                raise ValidationError(_(
                    'The notice period cannot be a negative number.'))

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'inom.offboarding.request') or _('New')
        return super().create(vals_list)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _load_checklist_from_templates(self):
        """Populate the clearance checklist from active templates."""
        self.ensure_one()
        if self.checklist_line_ids:
            return
        templates = self.env['inom.offboarding.checklist.template'].search([
            ('active', '=', True),
            '|',
            ('company_id', '=', self.company_id.id),
            ('company_id', '=', False),
        ])
        lines = [(0, 0, {
            'template_id': template.id,
            'name': template.name,
            'sequence': template.sequence,
            'responsible': template.responsible,
            'description': template.description,
        }) for template in templates]
        if lines:
            self.checklist_line_ids = lines

    # ------------------------------------------------------------------
    # Email helpers
    # ------------------------------------------------------------------
    def _get_employee_email(self):
        """Return the employee email, preferring work over private."""
        self.ensure_one()
        employee = self.employee_id
        return employee.work_email or employee.private_email or False

    def _get_manager_email(self):
        """Return the reporting manager email, preferring work over private."""
        self.ensure_one()
        manager = self.manager_id
        return manager.work_email or manager.private_email or False

    def _get_hr_team_emails(self):
        """Return a comma-separated list of HR manager emails."""
        hr_group = self.env.ref(
            'inom_employee_offboarding.inom_group_offboarding_hr',
            raise_if_not_found=False)
        if not hr_group:
            return False
        emails = hr_group.user_ids.filtered('email').mapped('email')
        return ','.join(emails) if emails else False

    def _send_offboarding_mail(self, template_xmlid, recipient_email):
        """Send a workflow email if a recipient address is available.

        Failures are logged but never block the workflow transition.
        """
        self.ensure_one()
        if not recipient_email:
            return
        template = self.env.ref(template_xmlid, raise_if_not_found=False)
        if not template:
            return
        try:
            template.send_mail(
                self.id,
                force_send=True,
                email_values={'email_to': recipient_email},
            )
        except Exception:
            # Email delivery problems should not break the process.
            self.message_post(body=_('Notification email could not be sent.'))

    # ------------------------------------------------------------------
    # Workflow actions
    # ------------------------------------------------------------------
    def action_submit_to_manager(self):
        for record in self:
            if record.state != 'draft':
                raise UserError(_(
                    'Only draft requests can be submitted to the manager.'))
            record._load_checklist_from_templates()
            record.state = 'manager_approval'
            record._send_offboarding_mail(
                'inom_employee_offboarding.mail_template_offboarding_submitted',
                record._get_manager_email())
        return True

    def action_manager_approve(self):
        for record in self:
            if record.state != 'manager_approval':
                raise UserError(_(
                    'This request is not awaiting manager approval.'))
            record.state = 'hr_approval'
            record._send_offboarding_mail(
                'inom_employee_offboarding.mail_template_offboarding_hr_review',
                record._get_hr_team_emails())
        return True

    def action_hr_approve(self):
        for record in self:
            if record.state != 'hr_approval':
                raise UserError(_(
                    'This request is not awaiting HR approval.'))
            record.state = 'approved'
            record._send_offboarding_mail(
                'inom_employee_offboarding.mail_template_offboarding_approved',
                record._get_employee_email())
        return True

    def action_relieve_employee(self):
        for record in self:
            if record.state != 'approved':
                raise UserError(_(
                    'Only approved requests can be relieved.'))
            if not record.relieving_date:
                raise UserError(_(
                    'Please set the relieving date before relieving '
                    'the employee.'))
            record.state = 'relieved'
            if record.employee_id:
                record._send_offboarding_mail(
                    'inom_employee_offboarding.mail_template_offboarding_relieved',
                    record._get_employee_email())
                record.employee_id.active = False
        return True

    def action_open_reject_wizard(self):
        self.ensure_one()
        return {
            'name': _('Reject Offboarding Request'),
            'type': 'ir.actions.act_window',
            'res_model': 'inom.offboarding.reject.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_request_id': self.id},
        }

    def action_reset_to_draft(self):
        for record in self:
            if record.state not in ('rejected', 'cancelled'):
                raise UserError(_(
                    'Only rejected or cancelled requests can be reset '
                    'to draft.'))
            record.state = 'draft'
            record.rejection_reason = False
        return True

    def action_cancel(self):
        for record in self:
            if record.state in ('relieved', 'cancelled'):
                raise UserError(_(
                    'This request can no longer be cancelled.'))
            record.state = 'cancelled'
        return True