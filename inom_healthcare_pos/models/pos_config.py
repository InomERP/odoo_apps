from odoo import models, fields, api, _
from odoo.exceptions import UserError


# ---------------------------------------------------------------------------
#  POS TYPE PROFILES
#  Each Healthcare POS terminal has a type that drives WHICH inom_healthcare_system
#  workflows, services and on-screen actions are surfaced. This is the single
#  source of truth: the backend ships the matching profile to the OWL client,
#  which renders only the relevant toolbar / panels for that type.
#  'service_types' filters the product grid; [] means "all". 'actions' are the
#  workflow buttons; each opens the matching backend record (prefilled with the
#  selected patient) or an in-POS patient action.
# ---------------------------------------------------------------------------
POS_TYPE_PROFILES = {
    'reception': {
        'label': 'Reception', 'icon': 'fa-user-plus', 'color': '#0d9488',
        'tagline': 'Registration & front desk',
        'service_types': ['consultation'],
        'show_doctor': False,
        'actions': [
            {'key': 'new_patient', 'label': 'Register Patient', 'icon': 'fa-user-plus', 'mode': 'patient_create'},
            {'key': 'find_patient', 'label': 'Find Patient', 'icon': 'fa-search', 'mode': 'patient_select'},
            {'key': 'appointment', 'label': 'Appointment', 'icon': 'fa-calendar-plus-o', 'mode': 'form', 'model': 'inom.appointment', 'needs_patient': True},
            {'key': 'queue', 'label': 'Queue / Token', 'icon': 'fa-ticket', 'mode': 'form', 'model': 'inom.queue', 'needs_patient': True},
        ],
    },
    'clinic': {
        'label': 'Clinic', 'icon': 'fa-stethoscope', 'color': '#2563eb',
        'tagline': 'Consultation & clinical care',
        'service_types': ['consultation', 'treatment', 'procedure'],
        'show_doctor': True,
        'actions': [
            {'key': 'find_patient', 'label': 'Select Patient', 'icon': 'fa-user', 'mode': 'patient_select'},
            {'key': 'visit', 'label': 'Patient Visit', 'icon': 'fa-clipboard', 'mode': 'form', 'model': 'patient.visit', 'needs_patient': True},
            {'key': 'clinical', 'label': 'Clinical Record', 'icon': 'fa-heartbeat', 'mode': 'form', 'model': 'inom.clinical', 'needs_patient': True},
            {'key': 'prescription', 'label': 'Prescription', 'icon': 'fa-file-text-o', 'mode': 'form', 'model': 'inom.prescription', 'needs_patient': True},
            {'key': 'history', 'label': 'History', 'icon': 'fa-history', 'mode': 'list', 'model': 'patient.history', 'needs_patient': True},
            {'key': 'allergy', 'label': 'Allergies', 'icon': 'fa-exclamation-triangle', 'mode': 'list', 'model': 'patient.allergy', 'needs_patient': True},
            {'key': 'vaccination', 'label': 'Vaccination', 'icon': 'fa-medkit', 'mode': 'list', 'model': 'patient.vaccination', 'needs_patient': True},
        ],
    },
    'pharmacy': {
        'label': 'Pharmacy', 'icon': 'fa-medkit', 'color': '#dc2626',
        'tagline': 'Dispensing & medicine sales',
        'service_types': ['pharmacy'],
        'show_doctor': False,
        'actions': [
            {'key': 'find_patient', 'label': 'Select Patient', 'icon': 'fa-user', 'mode': 'patient_select'},
            {'key': 'prescription', 'label': 'Prescriptions', 'icon': 'fa-file-text-o', 'mode': 'list', 'model': 'inom.prescription', 'needs_patient': True},
            {'key': 'insurance', 'label': 'Insurance Claim', 'icon': 'fa-shield', 'mode': 'form', 'model': 'inom.insurance.claim', 'needs_patient': True},
            {'key': 'stock', 'label': 'Medicine Stock', 'icon': 'fa-cubes', 'mode': 'list', 'model': 'inom.pharmacy', 'needs_patient': False},
        ],
    },
    'laboratory': {
        'label': 'Laboratory', 'icon': 'fa-flask', 'color': '#7c3aed',
        'tagline': 'Tests, sampling & reports',
        'service_types': ['lab'],
        'show_doctor': False,
        'actions': [
            {'key': 'find_patient', 'label': 'Select Patient', 'icon': 'fa-user', 'mode': 'patient_select'},
            {'key': 'lab_test', 'label': 'New Lab Test', 'icon': 'fa-flask', 'mode': 'form', 'model': 'inom.laboratory', 'needs_patient': True},
            {'key': 'lab_reports', 'label': 'Reports', 'icon': 'fa-file-text-o', 'mode': 'list', 'model': 'inom.laboratory', 'needs_patient': True},
            {'key': 'insurance', 'label': 'Insurance Claim', 'icon': 'fa-shield', 'mode': 'form', 'model': 'inom.insurance.claim', 'needs_patient': True},
        ],
    },
    'emergency': {
        'label': 'Emergency', 'icon': 'fa-ambulance', 'color': '#ea580c',
        'tagline': 'Urgent & casualty care',
        'service_types': [],  # everything is fair game in emergency
        'show_doctor': True,
        'actions': [
            {'key': 'new_patient', 'label': 'Register Patient', 'icon': 'fa-user-plus', 'mode': 'patient_create'},
            {'key': 'find_patient', 'label': 'Select Patient', 'icon': 'fa-user', 'mode': 'patient_select'},
            {'key': 'emergency', 'label': 'Emergency Case', 'icon': 'fa-ambulance', 'mode': 'form', 'model': 'inom.emergency', 'needs_patient': True},
            {'key': 'clinical', 'label': 'Clinical Record', 'icon': 'fa-heartbeat', 'mode': 'form', 'model': 'inom.clinical', 'needs_patient': True},
        ],
    },
    'general': {
        'label': 'General', 'icon': 'fa-hospital-o', 'color': '#0f766e',
        'tagline': 'All healthcare services',
        'service_types': [],
        'show_doctor': True,
        'actions': [
            {'key': 'new_patient', 'label': 'Register Patient', 'icon': 'fa-user-plus', 'mode': 'patient_create'},
            {'key': 'find_patient', 'label': 'Select Patient', 'icon': 'fa-user', 'mode': 'patient_select'},
            {'key': 'appointment', 'label': 'Appointment', 'icon': 'fa-calendar-plus-o', 'mode': 'form', 'model': 'inom.appointment', 'needs_patient': True},
        ],
    },
}


class HealthcarePosConfig(models.Model):
    """A Healthcare POS terminal / branch configuration.

    Each config is the unit of multi-branch & multi-company operation: it
    pins a company and a currency, lists the categories, services and payment
    methods exposed at that point of sale, and is the entry point a cashier
    opens a session against. Multiple configs can run concurrently, each with
    its own live session, which is how multi-session is achieved.
    """

    _name = 'healthcare.pos.config'
    _description = 'Healthcare POS Configuration'
    _order = 'sequence, name'

    name = fields.Char(string='Point of Sale', required=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)

    pos_type = fields.Selection([
        ('reception', 'Reception'),
        ('clinic', 'Clinic'),
        ('pharmacy', 'Pharmacy'),
        ('laboratory', 'Laboratory'),
        ('emergency', 'Emergency'),
        ('general', 'General / Branch'),
    ], string='POS Type', default='general', required=True,
        help="Drives which healthcare workflows, services and on-screen actions "
             "appear in this terminal. Each type shows only its relevant flow.")

    company_id = fields.Many2one(
        'res.company', string='Company', required=True,
        default=lambda self: self.env.company)
    currency_id = fields.Many2one(
        'res.currency', string='Currency',
        default=lambda self: self.env.company.currency_id,
        required=True,
        help="Currency this terminal operates in. Lets a branch in another "
             "country bill in its own currency.")

    # Branch location (re-uses the healthcare campus, falls back to free text).
    campus_id = fields.Many2one('inom.campus', string='Branch / Campus')
    location_note = fields.Char(string='Location')

    category_ids = fields.Many2many(
        'healthcare.pos.category', string='Available Categories',
        help="Leave empty to expose every category of the company.")
    payment_method_ids = fields.Many2many(
        'healthcare.pos.payment.method', string='Payment Methods')

    # Behaviour toggles -------------------------------------------------
    allow_create_patient = fields.Boolean(string='Create Patients in POS', default=True)
    require_patient = fields.Boolean(string='Patient Mandatory', default=True)
    generate_billing = fields.Boolean(
        string='Create Hospital Bill', default=True,
        help="On payment, create an inom.billing record for the patient.")
    generate_clinical_records = fields.Boolean(
        string='Create Clinical Records', default=True,
        help="On payment, create lab / radiology / treatment records for the "
             "matching service lines.")
    set_opening_balance = fields.Boolean(string='Cash Control', default=True)

    # Live session ------------------------------------------------------
    session_ids = fields.One2many('healthcare.pos.session', 'config_id', string='Sessions')
    current_session_id = fields.Many2one(
        'healthcare.pos.session', compute='_compute_current_session', string='Current Session')
    current_session_state = fields.Char(compute='_compute_current_session')
    session_count = fields.Integer(compute='_compute_session_count')
    order_count = fields.Integer(compute='_compute_order_count')

    @api.depends('session_ids', 'session_ids.state')
    def _compute_current_session(self):
        for rec in self:
            session = rec.session_ids.filtered(
                lambda s: s.state in ('opening_control', 'opened')
            )[:1]
            rec.current_session_id = session.id
            rec.current_session_state = session.state or 'closed'

    def _compute_session_count(self):
        for rec in self:
            rec.session_count = len(rec.session_ids)

    def _compute_order_count(self):
        data = self.env['healthcare.pos.order']._read_group(
            [('config_id', 'in', self.ids)], ['config_id'], ['__count'])
        mapped = {c.id: n for c, n in data}
        for rec in self:
            rec.order_count = mapped.get(rec.id, 0)

    # ------------------------------------------------------------------
    # Session lifecycle helpers
    # ------------------------------------------------------------------
    def open_session_cb(self):
        """Open (or resume) a session for the current user and launch the UI."""
        self.ensure_one()
        session = self.session_ids.filtered(
            lambda s: s.state in ('opening_control', 'opened')
            and s.user_id == self.env.user
        )[:1]
        if not session:
            session = self.env['healthcare.pos.session'].create({
                'config_id': self.id,
                'user_id': self.env.user.id,
            })
        return session.action_open_ui()

    def open_ui(self):
        """Launch the POS client action for this config."""
        self.ensure_one()
        return {
            'type': 'ir.actions.client',
            'tag': 'inom_healthcare_pos.app',
            'params': {'config_id': self.id},
        }

    def action_view_sessions(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Sessions'),
            'res_model': 'healthcare.pos.session',
            'view_mode': 'list,form',
            'views': [(False, 'list'), (False, 'form')],
            'domain': [('config_id', '=', self.id)],
            'context': {'default_config_id': self.id},
        }

    def action_view_orders(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Orders'),
            'res_model': 'healthcare.pos.order',
            'view_mode': 'list,form',
            'views': [(False, 'list'), (False, 'form')],
            'domain': [('config_id', '=', self.id)],
            'context': {'default_config_id': self.id},
        }

    # ------------------------------------------------------------------
    # Dashboard (Odoo-POS-style launcher) data
    # ------------------------------------------------------------------
    @api.model
    def get_pos_dashboard_data(self):
        """Return one card per accessible terminal for the POS dashboard.

        Record rules already scope the result by company, so each user only
        sees the terminals of the companies they are allowed in. Every card
        carries its own company / branch / currency and live-session status,
        which is what lets several locations run side by side.
        """
        Session = self.env['healthcare.pos.session']
        cards = []
        for config in self.search([]):
            session = config.current_session_id
            last_closed = Session.search([
                ('config_id', '=', config.id),
                ('state', '=', 'closed'),
            ], order='stop_at desc', limit=1)
            profile = POS_TYPE_PROFILES.get(config.pos_type) or POS_TYPE_PROFILES['general']
            cards.append({
                'id': config.id,
                'name': config.name,
                'pos_type': config.pos_type,
                'pos_type_label': profile.get('label', ''),
                'pos_type_icon': profile.get('icon', 'fa-hospital-o'),
                'pos_type_color': profile.get('color', '#0d9488'),
                'tagline': profile.get('tagline', ''),
                'company': config.company_id.name or '',
                'branch': config.campus_id.name or config.location_note or '',
                'currency': config.currency_id.symbol or config.currency_id.name or '',
                'currency_name': config.currency_id.name or '',
                'state': config.current_session_state or 'closed',
                'is_open': bool(session),
                'opened_by': session.user_id.name if session else '',
                'opened_by_me': bool(session and session.user_id.id == self.env.user.id),
                'started': fields.Datetime.to_string(session.start_at) if (session and session.start_at) else '',
                'session_orders': session.order_count if session else 0,
                'session_total': session.total_sales if session else 0.0,
                'session_count': config.session_count,
                'order_count': config.order_count,
                'last_closing_date': fields.Datetime.to_string(last_closed.stop_at) if (last_closed and last_closed.stop_at) else '',
                'last_closing_balance': last_closed.closing_balance if last_closed else 0.0,
            })
        return cards

    # ------------------------------------------------------------------
    # POS-type profile (drives the dynamic, type-specific UI)
    # ------------------------------------------------------------------
    def _pos_type_profile(self):
        """Return the UI profile for this terminal's type.

        Workflow actions that target a model which isn't installed in the
        current database are dropped, so the toolbar never offers a button
        that would fail to open.
        """
        self.ensure_one()
        import copy
        profile = copy.deepcopy(POS_TYPE_PROFILES.get(self.pos_type)
                                or POS_TYPE_PROFILES['general'])
        actions = []
        for act in profile.get('actions', []):
            model = act.get('model')
            if model and model not in self.env:
                continue
            actions.append(act)
        profile['actions'] = actions
        return profile

    # ------------------------------------------------------------------
    # Pharmacy bridge: mirror inom.pharmacy medicines as POS services
    # ------------------------------------------------------------------
    @api.model
    def _get_pharmacy_category(self):
        """Find (or create) the POS category pharmacy medicines map to."""
        Category = self.env['healthcare.pos.category'].sudo()
        cat = self.env.ref('inom_healthcare_pos.cat_pharmacy', raise_if_not_found=False)
        if cat:
            return cat
        cat = Category.search([('name', 'ilike', 'Pharmacy')], limit=1)
        if not cat:
            cat = Category.create({
                'name': 'Pharmacy', 'icon': 'medkit',
                'color': '#dc2626', 'sequence': 40,
            })
        return cat

    @api.model
    def _sync_pharmacy_services(self):
        """Create a sellable POS service for every active pharmacy medicine.

        Idempotent: services are matched to medicines on ``pharmacy_id`` so
        repeated calls never duplicate. Linked services pull live price and
        stock from the medicine and decrement its stock when sold. Returns the
        number of newly created services.
        """
        if 'inom.pharmacy' not in self.env:
            return 0
        Pharmacy = self.env['inom.pharmacy'].sudo()
        Service = self.env['healthcare.pos.service'].sudo()
        medicines = Pharmacy.search([('active', '=', True)])
        if not medicines:
            return 0

        category = self._get_pharmacy_category()
        existing = Service.with_context(active_test=False).search(
            [('pharmacy_id', 'in', medicines.ids)])
        by_med = {s.pharmacy_id.id: s for s in existing}

        created = 0
        for med in medicines:
            svc = by_med.get(med.id)
            if not svc:
                Service.create({
                    'name': med.name,
                    'code': med.code if (med.code and med.code != 'New') else False,
                    'category_id': category.id,
                    'service_type': 'pharmacy',
                    'pharmacy_id': med.id,
                    'track_stock': True,
                    'list_price': med.price or 0.0,
                    'available_in_pos': True,
                    'company_id': False,  # medicines are shared across companies
                })
                created += 1
            else:
                # Make sure a previously hidden/archived mirror comes back.
                vals = {}
                if not svc.available_in_pos:
                    vals['available_in_pos'] = True
                if not svc.active:
                    vals['active'] = True
                if vals:
                    svc.write(vals)
        return created

    def action_sync_pharmacy_services(self):
        """Manual trigger (header button) to refresh the pharmacy catalogue."""
        count = self._sync_pharmacy_services()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Pharmacy Sync'),
                'message': (_("%s new medicine(s) added to the POS catalogue.") % count)
                           if count else _("POS catalogue already up to date."),
                'type': 'success',
                'sticky': False,
            },
        }

    # ------------------------------------------------------------------
    # Frontend bootstrap data
    # ------------------------------------------------------------------
    def _get_categories(self):
        self.ensure_one()
        if self.category_ids:
            return self.category_ids
        return self.env['healthcare.pos.category'].search([
            ('active', '=', True),
            '|', ('company_id', '=', self.company_id.id), ('company_id', '=', False),
        ])

    def _get_payment_methods(self):
        self.ensure_one()
        if self.payment_method_ids:
            return self.payment_method_ids
        return self.env['healthcare.pos.payment.method'].search([
            ('active', '=', True),
            '|', ('company_id', '=', self.company_id.id), ('company_id', '=', False),
        ])

    @api.model
    def load_pos_data(self, config_id):
        """Return everything the OWL POS UI needs to bootstrap a terminal."""
        config = self.browse(config_id).exists()
        if not config:
            raise UserError(_("This Point of Sale configuration no longer exists."))
        config = config.sudo()
        company = config.company_id
        currency = config.currency_id

        # Auto-bridge pharmacy medicines (inom.pharmacy) into sellable POS
        # services so anything added in Pharmacy Management shows up in the
        # POS Pharmacy tab without manual catalogue entry. Never let a quirk
        # of the pharmacy model block the POS from opening.
        try:
            config._sync_pharmacy_services()
        except Exception:
            pass

        categories = config._get_categories()
        profile = config._pos_type_profile()
        allowed_types = profile.get('service_types') or []

        service_domain = [
            ('available_in_pos', '=', True),
            ('active', '=', True),
            ('category_id', 'in', categories.ids),
            '|', ('company_id', '=', company.id), ('company_id', '=', False),
        ]
        if allowed_types:
            service_domain.append(('service_type', 'in', allowed_types))
        services = self.env['healthcare.pos.service'].sudo().search(service_domain)

        # When a type restricts the catalogue, hide category tabs that ended up
        # with no services so the grid stays focused on the relevant flow.
        if allowed_types:
            visible_cat_ids = set(services.mapped('category_id').ids)
            categories = categories.filtered(lambda c: c.id in visible_cat_ids)
        payment_methods = config._get_payment_methods()

        patients = self.env['inom.patient'].sudo().search(
            [('active', '=', True)], order='name', limit=2000)
        doctors = self.env['inom.doctor'].sudo().search([], order='name')

        # Resume an open session for this user, if any.
        session = self.env['healthcare.pos.session'].sudo().search([
            ('config_id', '=', config.id),
            ('user_id', '=', self.env.user.id),
            ('state', 'in', ('opening_control', 'opened')),
        ], limit=1)

        return {
            'config': {
                'id': config.id,
                'name': config.name,
                'pos_type': config.pos_type,
                'pos_type_label': profile.get('label', ''),
                'pos_type_icon': profile.get('icon', 'fa-hospital-o'),
                'pos_type_color': profile.get('color', '#0d9488'),
                'features': {'show_doctor': profile.get('show_doctor', True)},
                'workflow_actions': profile.get('actions', []),
                'allow_create_patient': config.allow_create_patient,
                'require_patient': config.require_patient,
                'set_opening_balance': config.set_opening_balance,
                'campus': config.campus_id.name or config.location_note or '',
            },
            'company': {
                'id': company.id,
                'name': company.name,
                'street': company.street or '',
                'street2': company.street2 or '',
                'city': company.city or '',
                'state_code': company.state_id.code if company.state_id else '',
                'zip': company.zip or '',
                'country': company.country_id.name if company.country_id else '',
                'address': ', '.join(p for p in [
                    company.street, company.street2, company.city,
                    company.state_id.name if company.state_id else '',
                    company.zip, company.country_id.name if company.country_id else '',
                ] if p),
                'phone': company.phone or '',
                'email': company.email or '',
                'website': company.website or '',
                'vat': company.vat or '',
                'logo': (
                    'data:image/png;base64,%s' % company.logo.decode()
                    if company.logo else ''
                ),
            },
            'currency': {
                'id': currency.id,
                'name': currency.name,
                'symbol': currency.symbol,
                'position': currency.position,
                'decimals': currency.decimal_places,
            },
            'session': session._session_ui_data() if session else False,
            'categories': [{
                'id': c.id, 'name': c.name, 'icon': c.icon or 'stethoscope',
                'color': c.color or '#0d9488', 'sequence': c.sequence,
            } for c in categories],
            'services': [{
                'id': s.id, 'name': s.name, 'code': s.code or '',
                'category_id': s.category_id.id,
                'service_type': s.service_type,
                'price': s._get_live_price(),
                'tax_percent': s.tax_percent,
                'track_stock': s.track_stock,
                'stock': s.pharmacy_id.stock_qty if s.pharmacy_id else False,
                'color': s.color or c.color if (c := s.category_id) else '#0d9488',
            } for s in services],
            'payment_methods': [{
                'id': p.id, 'name': p.name, 'type': p.method_type,
                'is_cash': p.is_cash, 'icon': p.icon or 'money',
            } for p in payment_methods],
            'patients': [self.env['healthcare.pos.order']._patient_ui_data(p) for p in patients],
            'doctors': [{
                'id': d.id, 'name': d.name,
                'specialization': d.specialization or '',
            } for d in doctors],
        }
