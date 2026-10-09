from odoo import api, models
from odoo.exceptions import UserError


class InomStudent(models.Model):
    _inherit = 'inom.student'

    def _inom_billing_partner(self):
        """The partner a fee invoice is addressed to.

        The guardian who pays, falling back to the student. A university
        chasing an unpaid instalment writes to the person with the bank
        account, and a student in their first year usually does not have one.

        Where a student has several guardians, the one with a billing contact
        wins; failing that the first. That is a guess, and it is the right
        place to look when an invoice lands on the wrong doorstep — a
        `partner_id` set explicitly on the intended guardian settles it.
        """
        self.ensure_one()
        guardians = self.guardian_ids
        payer = guardians.filtered('partner_id')[:1] or guardians[:1]
        if payer:
            return payer._inom_ensure_partner()
        return self._inom_ensure_partner()

    def _inom_ensure_partner(self):
        """A contact record, created on demand rather than at enrolment.

        Most students never need one — only the ones being invoiced do, and
        creating six thousand partners at import time to serve a few hundred
        invoices clutters every partner list in the database.

        sudo, because a billing contact is bookkeeping rather than a decision.
        The accounts office is authorised to invoice a student; it is not, and
        should not be, authorised to create arbitrary contacts across the
        database — and the person who presses Pay on their own fee is the
        student, who has no rights on their own record at all. Without this,
        "Invoice everything due" refused with an access error naming
        res.partner, on a screen that never mentions contacts.

        What guards this is unchanged: the action is reached only by a caller
        holding its declared groups, and the only record written is the
        student's own.
        """
        self.ensure_one()
        if self.partner_id:
            return self.partner_id
        # sudo(): creates the student's own billing contact and links it; the
        # caller's rights were already checked on the action (docstring above).
        record = self.sudo()
        partner = record.env['res.partner'].create({
            'name': self.name,
            'email': self.email or False,
            'phone': self.phone or False,
            'company_id': self.company_id.id,
            'type': 'contact',
        })
        record.partner_id = partner
        return partner


class InomGuardian(models.Model):
    _inherit = 'inom.guardian'

    def _inom_ensure_partner(self):
        # sudo for the same reason as the student's: see the note there. The
        # missing-contact-details check stays above it, so a guardian who
        # cannot be reached is still refused — that is a billing decision, not
        # a permission.
        self.ensure_one()
        if self.partner_id:
            return self.partner_id
        if not (self.email or self.phone):
            raise UserError(
                f'{self.name} has no email or phone, so there is no way to send '
                f'an invoice. Add one before billing.')
        # sudo(): creates the guardian's own billing contact and links it; see
        # the note on the student's method.
        record = self.sudo()
        partner = record.env['res.partner'].create({
            'name': self.name,
            'email': self.email or False,
            'phone': self.phone or False,
            'company_id': self.company_id.id,
            'type': 'contact',
        })
        record.partner_id = partner
        return partner

    @api.model
    def _inom_portal_fields(self):
        return super()._inom_portal_fields() + ['partner_id']
