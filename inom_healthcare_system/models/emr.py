# -*- coding: utf-8 -*-
#
#  Electronic Medical Record (EMR) extension
#  ------------------------------------------
#  This module EXTENDS the existing ``inom.patient`` model. It only ADDS
#  computed convenience fields and helper actions used to surface a
#  patient's clinical history as smart buttons on the patient form.
#
#  It does not modify, remove or override any existing field, method or
#  workflow, so backward compatibility is fully preserved.
#
from odoo import models, fields, api


class InomPatientEMR(models.Model):
    _inherit = 'inom.patient'

    # ------------------------------------------------------------------
    # EMR summary counters (non-stored: computed on demand for the form)
    # ------------------------------------------------------------------
    visit_count = fields.Integer(
        string='Visits', compute='_compute_emr_counts')
    appointment_count = fields.Integer(
        string='Appointments', compute='_compute_emr_counts')
    lab_count = fields.Integer(
        string='Lab Tests', compute='_compute_emr_counts')
    radiology_count = fields.Integer(
        string='Radiology', compute='_compute_emr_counts')
    prescription_count = fields.Integer(
        string='Prescriptions', compute='_compute_emr_counts')
    surgery_count = fields.Integer(
        string='Surgeries', compute='_compute_emr_counts')
    billing_count = fields.Integer(
        string='Bills', compute='_compute_emr_counts')
    allergy_count = fields.Integer(
        string='Allergies', compute='_compute_emr_counts')

    def _compute_emr_counts(self):
        """Aggregate related clinical records per patient.

        Uses ``read_group`` so the whole recordset is resolved in one
        query per related model instead of one query per patient.
        """
        models_map = {
            'visit_count': 'patient.visit',
            'appointment_count': 'inom.appointment',
            'lab_count': 'inom.laboratory',
            'radiology_count': 'inom.radiology',
            'prescription_count': 'inom.prescription',
            'surgery_count': 'inom.surgery',
            'billing_count': 'inom.billing',
            'allergy_count': 'patient.allergy',
        }
        ids = self.ids
        # Pre-fill zeros (covers new/unsaved records too).
        for rec in self:
            for fname in models_map:
                rec[fname] = 0
        if not ids:
            return
        for fname, model in models_map.items():
            grouped = self.env[model]._read_group(
                [('patient_id', 'in', ids)],
                groupby=['patient_id'],
                aggregates=['__count'],
            )
            counts = {patient.id: count for patient, count in grouped}
            for rec in self:
                rec[fname] = counts.get(rec.id, 0)

    # ------------------------------------------------------------------
    # Smart-button actions – open related history filtered by patient
    # ------------------------------------------------------------------
    def _emr_action(self, name, model):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': name,
            'res_model': model,
            'view_mode': 'list,form',
            'domain': [('patient_id', '=', self.id)],
            'context': {'default_patient_id': self.id},
        }

    def action_view_visits(self):
        return self._emr_action('Visits', 'patient.visit')

    def action_view_appointments(self):
        return self._emr_action('Appointments', 'inom.appointment')

    def action_view_labs(self):
        return self._emr_action('Lab Tests', 'inom.laboratory')

    def action_view_radiology(self):
        return self._emr_action('Radiology', 'inom.radiology')

    def action_view_prescriptions(self):
        return self._emr_action('Prescriptions', 'inom.prescription')

    def action_view_surgeries(self):
        return self._emr_action('Surgeries', 'inom.surgery')

    def action_view_bills(self):
        return self._emr_action('Bills', 'inom.billing')

    def action_view_allergies(self):
        return self._emr_action('Allergies', 'patient.allergy')
