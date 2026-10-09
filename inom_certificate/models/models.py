import secrets

from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError


class InomCertificateType(models.Model):
    _name = 'inom.certificate.type'
    _description = 'Certificate Type'
    _inherit = ['inom.mixin']
    _order = 'name'

    name = fields.Char(required=True)
    code = fields.Char(required=True, size=16, index=True)
    description = fields.Text()
    template_ref = fields.Char(
        string='QWeb template',
        help='External id of the report template used to render this certificate.')
    approver_group_id = fields.Many2one(
        'res.groups', string='Approved by',
        help='Only members of this group may approve a request of this type.')
    requires_no_dues = fields.Boolean(
        default=False,
        help='Blocks approval while the student has an outstanding fee balance.')
    fee = fields.Monetary()
    currency_id = fields.Many2one(
        'res.currency', default=lambda s: s.env.company.currency_id, required=True)
    turnaround_days = fields.Integer(default=3)

    _code_uniq = models.Constraint(
        'UNIQUE(code, company_id)',
        'That certificate code is already in use.')

    @api.model
    def _inom_portal_fields(self):
        return ['id', 'display_name', 'name', 'code', 'description',
                'requires_no_dues', 'fee', 'turnaround_days', 'currency_id',
                'approver_group_id']


class InomCertificateRequest(models.Model):
    _name = 'inom.certificate.request'
    _description = 'Certificate Request'
    _inherit = ['inom.mixin']
    _order = 'requested_on desc'
    _rec_name = 'reference'
    _rec_names_search = ('reference', 'student_id.name',
                         'student_id.enrolment_no')

    reference = fields.Char(required=True, copy=False, readonly=True, index=True,
                            default=lambda self: 'New')
    type_id = fields.Many2one('inom.certificate.type', required=True, index=True)
    student_id = fields.Many2one('inom.student', required=True, index=True)
    department_id = fields.Many2one(
        'inom.department', related='student_id.department_id', store=True, index=True)

    requested_on = fields.Date(required=True, default=fields.Date.context_today)
    purpose = fields.Text(required=True)
    issued_on = fields.Date(readonly=True, copy=False)
    approver_id = fields.Many2one('res.users', readonly=True, copy=False)
    rejection_reason = fields.Char(readonly=True, copy=False)

    verification_code = fields.Char(
        readonly=True, copy=False, index=True,
        help='Printed on the certificate. An employer checks it at the public '
             'verification page.')

    state = fields.Selection(
        [('draft', 'Draft'), ('pending', 'Awaiting approval'),
         ('approved', 'Approved'), ('issued', 'Issued'), ('rejected', 'Rejected')],
        default='draft', required=True, index=True, tracking=True)

    _reference_uniq = models.Constraint(
        'UNIQUE(reference, company_id)',
        'That request reference is already in use.')
    _verification_uniq = models.Constraint(
        'UNIQUE(verification_code)',
        'Verification codes must be unique.')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('reference', 'New') == 'New':
                # sudo(): a sequence is technical configuration, closed to
                # portal users. A student raising their own certificate request
                # was refused here — and the message said "you do not have
                # access to that", which points at the certificate rather than
                # at the numbering they never asked about.
                vals['reference'] = self.env['ir.sequence'].sudo().next_by_code(
                    'inom.certificate.request') or 'New'
        return super().create(vals_list)

    def write(self, vals):
        """An issued certificate is a document somebody is holding.

        Editing one after the fact means the paper in an employer's hand no
        longer matches the register it is verified against — which is exactly
        the failure the register exists to prevent. Reissue instead.
        """
        protected = {'type_id', 'student_id', 'purpose', 'issued_on', 'verification_code'}
        if protected & set(vals):
            issued = self.filtered(lambda r: r.state == 'issued')
            if issued:
                raise ValidationError(
                    'These certificates are already issued. Raise a fresh request '
                    'rather than editing the register.')
        return super().write(vals)

    # ------------------------------------------------------------------
    def _inom_action_submit(self, payload=None):
        """Send a draft for approval.

        The one state change the owner is meant to make, and the guard below
        was blocking it — with a message telling them to press the button they
        had just pressed.

        Writes through a context flag rather than relaxing the guard, so
        `state` stays closed to a direct write. The flag is set here and
        nowhere else, which means there is still no path to `approved` that
        does not go through an approver.
        """
        self.ensure_one()
        if self.state != 'draft':
            raise ValidationError('Only a draft request can be submitted.')
        self.with_context(inom_certificate_submit=True).write({'state': 'pending'})
        return {'state': 'pending'}

    def _inom_action_approve(self, payload=None):
        self.ensure_one()
        if self.state != 'pending':
            raise ValidationError('Only a pending request can be approved.')
        group = self.type_id.approver_group_id
        # sudo() to read the membership; a student raising a request reaches
        # this, and res.groups is closed to them.
        if group and group not in self.env.user.sudo().group_ids:
            raise ValidationError(
                f'A {self.type_id.name} is approved by {group.name}, not by your role.')
        self._check_no_dues()
        self.write({'state': 'approved', 'approver_id': self.env.user.id})
        return {'state': 'approved'}

    def _check_no_dues(self):
        """Block approval while fees are outstanding, where that is the rule.

        Guarded on the model being present: a university that does not bill
        fees through this system still needs certificates to work.
        """
        self.ensure_one()
        if not self.type_id.requires_no_dues:
            return
        if 'inom.fee.account' not in self.env:
            return
        outstanding = self.env['inom.fee.account'].search([
            ('student_id', '=', self.student_id.id), ('amount_due', '>', 0),
        ])
        if outstanding:
            raise ValidationError(
                f'{self.student_id.name} has an outstanding fee balance. '
                f'A {self.type_id.name} needs a no-dues position first.')

    def _inom_action_issue(self, payload=None):
        self.ensure_one()
        if self.state != 'approved':
            raise ValidationError('Approve the request before issuing it.')
        self.write({
            'state': 'issued',
            'issued_on': fields.Date.context_today(self),
            # token_hex, not a sequence: a predictable verification code lets
            # anyone mint a plausible-looking one for a certificate that was
            # never issued.
            'verification_code': secrets.token_hex(8).upper(),
        })
        return {'verification_code': self.verification_code}

    def _inom_action_reject(self, payload=None):
        self.ensure_one()
        reason = (payload or {}).get('reason')
        if not reason:
            raise ValidationError('Say why, so the student knows what to fix.')
        self.write({'state': 'rejected', 'rejection_reason': reason,
                    'approver_id': self.env.user.id})
        return {'state': 'rejected'}

    @api.model
    def _inom_portal_fields(self):
        return ['id', 'display_name', 'reference', 'type_id', 'student_id',
                'requested_on', 'purpose', 'issued_on', 'verification_code',
                'state', 'rejection_reason']


class InomCertificateRequestReport(models.Model):
    _inherit = 'inom.certificate.request'

    def _inom_verify_url(self):
        """The address printed on the certificate.

        Built from web.base.url so it points at the public hostname rather
        than localhost — a certificate carrying an unreachable verification
        address is worse than one carrying none.
        """
        self.ensure_one()
        base = self.env['ir.config_parameter'].sudo().get_str(
            'web.base.url', '')  # standard Odoo config read
        return f'{base}/verify/{self.verification_code}' if self.verification_code else ''

    def _inom_action_download(self, payload=None):
        self.ensure_one()
        if self.state != 'issued':
            raise ValidationError(
                'Issue the certificate before printing it. An unissued '
                'certificate has no verification code.')
        return {'open_url': f'/ums/report/certificate/{self.id}'}


def _register_certificate_reports():
    from odoo.addons.inom_portal.controllers.report import register_report
    register_report(
        'certificate', 'inom_certificate.action_report_certificate',
        'inom.certificate.request',
        lambda r: f'certificate-{r.reference.replace("/", "-")}')


_register_certificate_reports()


class InomCertificateRequestSelf(models.Model):
    """A student requesting for themselves.

    The form offered a Student picker, which is wrong twice over: a student
    has exactly one answer, and choosing anyone else is refused by the record
    rule — as an access error at save time, after the form was filled in.

    Pinned server-side rather than only hidden on the form. The screen is what
    a browser sends; this is what the system accepts.
    """
    _inherit = 'inom.certificate.request'

    @api.model_create_multi
    def create(self, vals_list):
        if not self._inom_may_approve():
            own = self.env['inom.student'].search(
                [('user_id', '=', self.env.uid)], limit=1)
            if own:
                for vals in vals_list:
                    chosen = vals.get('student_id')
                    if chosen and chosen != own.id:
                        raise UserError(
                            'You can only request a certificate for yourself.')
                    vals['student_id'] = own.id
            elif any(not v.get('student_id') for v in vals_list):
                raise UserError(
                    'Your account is not linked to a student record, so a '
                    'certificate cannot be requested for you. Ask the '
                    "registrar's office.")
        return super().create(vals_list)

    @api.model
    def _inom_locked_for_user(self):
        """A student does not choose whose request this is.

        create() pins it and refuses anything else. Telling the form makes the
        field read-only instead of offering a choice that will be rejected.
        """
        return [] if self._inom_may_approve() else ['student_id']

    @api.model
    def default_get(self, fields_list):
        """Fill the student in for a student, so the field is answered."""
        values = super().default_get(fields_list)
        if 'student_id' in fields_list and not self._inom_may_approve():
            own = self.env['inom.student'].search(
                [('user_id', '=', self.env.uid)], limit=1)
            if own:
                values['student_id'] = own.id
        return values


class InomCertificateRequestGuard(models.Model):
    """A student may raise a request. They may not approve it.

    Same shape as the submission guard: the ACL grants write so a student can
    correct the purpose on a draft, and the record rule scopes them to their
    own requests. Neither prevents them writing `state` directly through the
    generic endpoint, and `state` is the field that decides whether a
    certificate exists.
    """
    _inherit = 'inom.certificate.request'

    APPROVER_FIELDS = {'state', 'issued_on', 'verification_code', 'approver_id',
                       'rejection_reason'}

    def _inom_may_approve(self):
        user = self.env.user
        return (self.env.su
                or user.has_group('inom_base.group_inom_registrar')
                or user.has_group('inom_base.group_inom_dean'))

    def write(self, vals):
        # The owner submitting their own draft is the exception, and it is
        # narrow: only from _inom_action_submit, only to 'pending', and only
        # on a record the record rules already scope to them.
        submitting = (self.env.context.get('inom_certificate_submit')
                      and set(vals) == {'state'}
                      and vals.get('state') == 'pending')
        if (self.APPROVER_FIELDS & set(vals) and not submitting
                and not self._inom_may_approve()):
            raise AccessError(
                'Only the Registrar or Dean can approve or issue a '
                'certificate.')
        if not self._inom_may_approve() and not submitting:
            locked = self.filtered(lambda r: r.state != 'draft')
            if locked:
                raise AccessError(
                    'This request has already been submitted and can no longer '
                    'be edited.')
        return super().write(vals)

    @api.model_create_multi
    def create(self, vals_list):
        if not self._inom_may_approve():
            for vals in vals_list:
                for name in self.APPROVER_FIELDS:
                    vals.pop(name, None)
        return super().create(vals_list)
