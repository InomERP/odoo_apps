from odoo import models, fields, api


class OehDashboard(models.TransientModel):
    _name = 'oeh.dashboard'
    _description = 'Hospital Dashboard'

    @api.model
    def get_dashboard_data(self):
        """Return all aggregated key data for the hospital dashboard.

        This method only *reads* existing data; it does not change any
        existing model, field or business logic.
        """
        env = self.env

        def count(model, domain=None):
            return env[model].search_count(domain or [])

        def total(model, field, domain=None):
            recs = env[model].search(domain or [])
            return round(sum(recs.mapped(field) or [0.0]), 2)

        def by_selection(model, field, selection):
            """Return ordered [{key,label,count}] for a selection field."""
            result = []
            for key, label in selection:
                result.append({
                    'key': key,
                    'label': label,
                    'count': count(model, [(field, '=', key)]),
                })
            return result

        today = fields.Date.context_today(self)

        # ---- Top KPIs -------------------------------------------------
        kpis = {
            'patients': count('oeh.patient'),
            'doctors': count('oeh.doctor'),
            'appointments': count('oeh.appointment'),
            'appointments_today': count('oeh.appointment', [
                ('appointment_date', '>=', '%s 00:00:00' % today),
                ('appointment_date', '<=', '%s 23:59:59' % today),
            ]),
            'surgeries': count('oehealth.surgery'),
            'lab_tests': count('oeh.laboratory'),
            'radiology': count('oeh.radiology'),
            'ipd_admitted': count('oeh.ipd', [('status', '=', 'admitted')]),
            'emergency': count('oeh.emergency'),
            'queue_waiting': count('oeh.queue', [('state', '=', 'waiting')]),
        }

        # ---- Breakdown charts ----------------------------------------
        appointments_by_state = by_selection('oeh.appointment', 'state', [
            ('draft', 'Draft'),
            ('confirm', 'Confirmed'),
            ('progress', 'In Progress'),
            ('done', 'Done'),
            ('cancel', 'Cancelled'),
        ])

        surgery_by_status = by_selection('oehealth.surgery', 'status', [
            ('draft', 'Draft'),
            ('scheduled', 'Scheduled'),
            ('progress', 'In Progress'),
            ('done', 'Done'),
            ('cancel', 'Cancelled'),
        ])

        lab_by_status = by_selection('oeh.laboratory', 'status', [
            ('draft', 'Draft'),
            ('done', 'Done'),
        ])

        radiology_by_status = by_selection('oeh.radiology', 'status', [
            ('draft', 'Draft'),
            ('done', 'Done'),
        ])

        emergency_by_triage = by_selection('oeh.emergency', 'triage_level', [
            ('low', 'Low'),
            ('medium', 'Medium'),
            ('high', 'Critical'),
        ])

        # ---- Beds -----------------------------------------------------
        bed_status = by_selection('oeh.bed', 'status', [
            ('free', 'Free'),
            ('occupied', 'Occupied'),
            ('maintenance', 'Maintenance'),
        ])
        beds_total = count('oeh.bed')

        # ---- Finance --------------------------------------------------
        billing = {
            'total_billed': total('oeh.billing', 'total_amount'),
            'total_paid': total('oeh.billing', 'paid_amount'),
            'total_balance': total('oeh.billing', 'balance'),
            'by_status': by_selection('oeh.billing', 'status', [
                ('draft', 'Draft'),
                ('partial', 'Partial'),
                ('paid', 'Paid'),
            ]),
        }

        insurance = {
            'count': count('oeh.insurance.claim'),
            'claim_amount': total('oeh.insurance.claim', 'claim_amount'),
            'approved_amount': total('oeh.insurance.claim', 'approved_amount'),
            'by_status': by_selection('oeh.insurance.claim', 'claim_status', [
                ('draft', 'Draft'),
                ('submitted', 'Submitted'),
                ('approved', 'Approved'),
                ('rejected', 'Rejected'),
            ]),
        }

        payments_total = total('oeh.payment', 'amount')

        # ---- Pharmacy -------------------------------------------------
        pharmacy = {
            'medicines': count('oeh.pharmacy'),
            'low_stock': count('oeh.pharmacy', [('is_low_stock', '=', True)]),
            'batches': count('oeh.medicine.batch'),
        }

        currency = env.company.currency_id

        return {
            'company': env.company.name,
            'currency_symbol': currency.symbol or '',
            'currency_position': currency.position or 'before',
            'kpis': kpis,
            'appointments_by_state': appointments_by_state,
            'surgery_by_status': surgery_by_status,
            'lab_by_status': lab_by_status,
            'radiology_by_status': radiology_by_status,
            'emergency_by_triage': emergency_by_triage,
            'bed_status': bed_status,
            'beds_total': beds_total,
            'billing': billing,
            'insurance': insurance,
            'payments_total': payments_total,
            'pharmacy': pharmacy,
        }
