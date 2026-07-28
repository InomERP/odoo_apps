# -*- coding: utf-8 -*-
{
    'name': 'Inom Job Cost Estimation | Cost Sheet, Estimated vs Actual, Markup & '
            'Margin, Revisions, Customer Portal Approval, Dashboard',
    'version': '19.0.2.0.0',
    'category': 'Sales',
    'summary': 'Build construction-style job cost estimates from material, '
               'manpower, equipment and indirect cost. Visual Cost Sheet with '
               'markup, discount and margin; quantity takeoff; revisions; '
               'rate cards; multi-level approval; customer portal approval; win/loss tracking; a no-JS dashboard; '
               'estimated vs actual variance; and one-click convert to a sales '
               'quotation.',
    'description': """
Job Cost Estimation
===================
A construction-style Cost Sheet, not a plain Odoo form
------------------------------------------------------
Every estimate opens on a visual Project Cost Summary: a cost-bucket donut,
per-bucket bars, and a running Total Cost, Profit, Selling Price, Taxes and
Final Price. Markup, discount and margin update live as you type, so the sheet
reads like dedicated estimation software rather than a data-entry screen.
Build the estimate from four cost buckets
-----------------------------------------
Break a job down into material, manpower, equipment and indirect cost. Material
lines pull unit cost from the product; manpower lines calculate from persons,
hours and hourly rate; equipment lines from units, duration and a rate basis
(hour/day/week/month); indirect costs are entered as flat amounts. Reusable
templates fill a whole estimate in one click for jobs you quote repeatedly.
Quantity takeoff / measurement sheet
------------------------------------
Drive any material quantity from a measurement sheet - count, length, area or
volume, with a deduct flag for openings - instead of typing a number. The line
quantity stays in sync with the takeoff and copies onto revisions.
Price it the way you actually quote
-----------------------------------
Apply markup on top of cost, add a header or per-line discount that visibly eats
margin, and add sale taxes on the estimate itself, so the figure the customer
sees is the figure they pay. A history-based markup suggestion and a cost
benchmark against similar past jobs help you price with confidence.
Know whether your jobs actually made money
------------------------------------------
Link every estimate to a project and analytic account and compare estimated
cost against what is really posted from timesheets, vendor bills and invoices.
A dedicated Cost Control tab shows estimated cost, actual cost, actual revenue
and the variance in both amount and percent.
Manage revisions, and let customers approve online
--------------------------------------------------
Every change becomes a numbered revision linked back to the original, with the
full history and an approval audit log one click away. Send the estimate and let
the customer accept it from the portal - recorded with signer name and timestamp
- without ever bypassing your internal approval threshold.
Track why you win and why you lose
----------------------------------
Reject with a mandatory, configurable loss reason, group your pipeline by it,
and see a "Why We Lost" panel that quietly disappears when nothing is lost.
See the whole pipeline at a glance
----------------------------------
A dashboard built without a line of JavaScript: KPI cards, a value trend, a
status donut, a cost-mix donut, a pipeline funnel, top customers and materials,
period-vs-previous, estimated-vs-actual and performance by job category, all
filterable by period.
Control who can approve what
----------------------------
Set an approval threshold in Settings. Estimates above it can only be approved
by a Job Costing Manager, whether the approval comes from the back office or a
customer accepting online.
Convert to a quotation without losing value
-------------------------------------------
Approved estimates become sales quotations where every bucket arrives as priced
lines at the marked-up rate, with per-line discount, taxes, rounding and
analytic distribution carried across so the two documents always agree.
Multi-currency conversion uses the customer pricelist currency at the estimate
date's rate. A smart button links the quotation straight back to its estimate.
Customer-safe by design
-----------------------
The customer PDF, portal and email show sell-side figures only. A separate,
access-restricted Internal Cost Sheet carries cost, markup and margin, plus
Material Requirement and Manpower Plan reports for the site team.
Suited to
---------
Contractors, construction and fabrication shops, interior fit-out, signage,
engineering services, repair and maintenance businesses, and any team that
quotes work as a mix of materials, people, equipment and overhead.
Features
--------
* Visual construction-style Cost Sheet with donut, bucket bars and live totals
* Four cost buckets: material, manpower, equipment and indirect cost
* Markup and margin engine with per-line markup override
* Header and per-line discount that reduces margin
* Quantity takeoff / measurement sheet with deduct flag
* Reusable rate cards for material and manpower unit costs
* Multi-level approval (User / Manager / Director) by amount threshold
* Budget vs estimated cost comparison
* History-based markup suggestion and similar-job cost benchmark
* Manpower lines linked to employees and job positions
* Project link that fills in the analytic account
* Estimated vs actual cost variance in a Cost Control tab
* Revision and versioning with full history and an approval audit log
* Customer portal online approval with signer name and timestamp
* Approval by amount threshold with a dedicated manager group
* Win/loss tracking with configurable loss reasons
* No-JavaScript analytics dashboard with period filters
* Reusable estimate templates with a recommended-template hint
* Sale taxes and configurable final-price rounding on the estimate
* Multi-currency and multi-company
* Documents tab separate from chatter attachments
* Daily expiry reminder that schedules an activity
* Convert to sales quotation with a two-way link
* Customer PDF, portal and email showing sell-side figures only
* Restricted Internal Cost Sheet, Material Requirement and Manpower Plan reports
* List, kanban, calendar, pivot, graph and activity views
""",
    'author': 'InomERP',
    'company': 'InomERP',
    'maintainer': 'InomERP',
    'website': 'https://inomerp.in',
    'support': 'info@inomerp.in',
    'license': 'OPL-1',
    'depends': [
        'sale_management',
        'account',
        'mail',
        'portal',
        'hr',
        'project',
    ],
    'data': [
        'security/inom_security.xml',
        'security/ir.model.access.csv',
        'data/ir_sequence.xml',
        'data/product_data.xml',
        'data/ir_cron.xml',
        'data/loss_reason_data.xml',
        'report/inom_estimate_report.xml',
        'data/mail_template.xml',
        'views/inom_cost_category_views.xml',
        'views/inom_cost_template_views.xml',
        'views/inom_rate_card_views.xml',
        'views/inom_takeoff_views.xml',
        'views/inom_cost_estimate_views.xml',
        'views/sale_order_views.xml',
        'views/inom_config_settings_views.xml',
        'views/inom_menus.xml',
        'views/inom_loss_reason_views.xml',
        'views/inom_dashboard_views.xml',
        'views/inom_portal_templates.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'inom_job_cost_estimation/static/src/scss/inom_cost_sheet.scss',
            'inom_job_cost_estimation/static/src/scss/inom_dashboard.scss',
        ],
    },
    'images': ['static/description/banner.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
}
