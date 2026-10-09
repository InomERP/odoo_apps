from odoo import api, fields, models


class InomPortalBulk(models.AbstractModel):
    _inherit = 'inom.portal.bulk'

    # ------------------------------------------------------------------
    # Invoice every instalment that is due, across a batch or a whole year.
    # ------------------------------------------------------------------
    @api.model
    def _bulk_fee_invoice_preview(self, params):
        lines, blocked = self._fee_invoice_scope(params)
        return self._preview(
            'Issue fee invoices',
            lines, blocked,
            note='Only instalments that are already due are invoiced. Billing a '
                 'student in July for an instalment payable next March is how a '
                 'university ends up explaining its own invoices.')

    @api.model
    def _bulk_fee_invoice_run(self, job, params):
        lines, _blocked = self._fee_invoice_scope(params)
        succeeded, failures = self._run_each(
            job, lines, lambda line: line._inom_action_issue_invoice(),
            label=lambda l: f'{l.account_id.student_id.name} — {l.name}')
        return {
            'succeeded': succeeded,
            'failed': len(failures),
            'failures': failures,
            'summary': f'{succeeded} invoice(s) posted, {len(failures)} could not be.',
        }

    @api.model
    def _fee_invoice_scope(self, params):
        """What would be invoiced, and what would not — with reasons.

        Read with the caller's own rights throughout, so a Dean previewing this
        sees their scope and not the university's.
        """
        Line = self.env['inom.fee.account.line']
        today = fields.Date.context_today(self)

        domain = [('move_id', '=', False), ('due_date', '<=', today)]
        if params.get('batch_id'):
            domain.append(('account_id.student_id.batch_id', '=', int(params['batch_id'])))
        if params.get('year_id'):
            domain.append(('account_id.year_id', '=', int(params['year_id'])))
        if params.get('department_id'):
            domain.append(('account_id.department_id', '=', int(params['department_id'])))

        candidates = Line.search(domain, order='due_date')
        eligible = Line.browse()
        blocked = []
        for line in candidates:
            account = line.account_id
            student = account.student_id
            if student.state not in ('enrolled', 'leave'):
                blocked.append({'name': f'{student.name} — {line.name}',
                                'reason': f'Student is {student.state}.'})
            elif account.structure_id.state != 'published':
                blocked.append({'name': f'{student.name} — {line.name}',
                                'reason': 'Fee structure is not published.'})
            elif not (student.guardian_ids.filtered('partner_id')
                      or student.guardian_ids or student.partner_id
                      or student.email or student.phone):
                # Caught here rather than at post time: an invoice with nobody
                # to send it to is a debt the university cannot chase.
                blocked.append({'name': f'{student.name} — {line.name}',
                                'reason': 'No guardian or contact details to bill.'})
            else:
                eligible |= line
        return eligible, blocked
