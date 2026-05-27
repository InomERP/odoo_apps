{
    'name': 'Inom Health Care System',

    'version': '18.0.1.0',

    'category': 'Healthcare',

    'summary': 'Comprehensive Odoo Healthcare & Hospital Management System for Patients, Doctors, Appointments, Surgery, Pharmacy, Billing, Laboratory, IPD, ICU, and Clinical Operations',

    'description': """
        Hospital Management System Core

        Features:
        - Patient Management
        - Medical History
        - Vaccination Tracking
        - Doctor Management
        - Appointment Scheduling
        - Queue Management
        - Clinical Evaluations
        - Prescriptions
        - Treatments & Procedures

        - Surgery Management
        - OT Scheduling
        - Surgical Team & Supplies
        - ASA / Mallampati / RCRI
        - Anesthesia Records

        - Pharmacy Management
        - Prescription Dispensing
        - Batch & Expiry Tracking
    """,

    'author': 'InomERP',

    'website': 'https://inomerp.in',

    'maintainer': 'InomERP',

    'support': 'info@inomerp.in',

    'license': 'LGPL-3',

    'depends': [
        'base', 'web',
        'mail',
        'contacts',
        'account',

        # Doctor integration
        'hr',
        'hr_attendance',
        'hr_holidays',
        'crm',
        'calendar',
    ],

    'data': [

        # Security
        'security/hospital_security.xml',
        'security/ir.model.access.csv',


        # Sequences
        'data/patient_sequence.xml',
        'data/clinic_sequence.xml',
        'data/specialty_sequence.xml',
        'data/pharmacy_sequence.xml',
        'data/operations_sequence.xml',
        'data/finance_sequence.xml',

        # Patient Management
        'views/patient_views.xml',
        'views/emr_views.xml',

        # Appointment & Consultation
        'views/doctor_views.xml',
        'views/appointment_views.xml',
        'views/queue_views.xml',

        # Clinical
        'views/clinical_views.xml',
        'views/prescription_views.xml',
        'views/treatment_views.xml',
        'views/certificate_views.xml',
        'views/icd_views.xml',
        'views/consent_views.xml',

        # Diagnostics
        'views/laboratory_views.xml',
        'views/sample_views.xml',
        'views/radiology_views.xml',

        # Surgery
        'views/surgery_views.xml',
        'views/ot_schedule_views.xml',
        'views/anesthesia_views.xml',
        # 'views/surgical_team_views.xml',

        # Pharmacy
        'views/pharmacy_views.xml',
        'views/prescription_dispense_views.xml',
        'views/medicine_batch_views.xml',

        #speciality care
        'views/pediatric_views.xml',
        'views/therapy_views.xml',
        'views/dental_views.xml',
        'views/gynecology_views.xml',

        #hospital
        'views/building_views.xml',
        'views/ward_views.xml',
        'views/bed_views.xml',
        'views/ipd_views.xml',
        'views/icu_views.xml',
        'views/emergency_views.xml',
        'views/nursing_views.xml',
        'views/campus_views.xml',

        #finacnce
        'views/billing_views.xml',
        'views/payment_views.xml',
        'views/insurance_claim_views.xml',
        'views/hcfa_edi_views.xml',
        'views/pre_authorization_views.xml',
        'report/finance_reports.xml',
        'report/clinic_reports.xml',

        # Communication
        'views/communication_views.xml',

        # Menu always last
        'views/menu.xml',

        # Dashboard (depends on the Health root menu defined in menu.xml)
        'views/dashboard_views.xml',

    ],

    'assets': {
        'web.assets_backend': [
            'inom_healthcare_system/static/src/css/dashboard.css',
            'inom_healthcare_system/static/src/js/dashboard.js',
            'inom_healthcare_system/static/src/xml/dashboard.xml',
        ],
    },

      'images': [
        'static/description/banner.png',
    ],

    'application': True,

    'installable': True,
}
