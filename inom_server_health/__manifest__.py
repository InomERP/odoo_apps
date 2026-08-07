{
    "name": "Server Health Monitor",
    "version": "19.0.6.2.0",
    "category": "Productivity",
    "summary": "Live host, PostgreSQL and Odoo health without loading the server",
    "description": """
Real-time health dashboard for self-hosted Odoo.

Shows CPU, memory (container-aware), disk, PostgreSQL connections and cache
hit ratio, worker RSS against the configured limits, late crons and the
outgoing mail queue.

Built to stay out of the way: no blocking calls, no per-poll writes, one
PostgreSQL round trip, per-metric caching and a single-flight guard so slow
probes never stack up on worker slots.
    """,
    "author": "Sachin Prajapati",
    "website": "https://inomerp.in",
    "license": "LGPL-3",
    # "base" is not listed: every module depends on it transitively
    # through "web" and "mail", so naming it adds nothing to the load graph.
    "depends": ["web", "mail"],
    "external_dependencies": {"python": ["psutil"]},
    "data": [
        "security/health_groups.xml",
        "security/ir.model.access.csv",
        "security/health_rules.xml",
        "data/health_data.xml",
        "views/health_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "inom_server_health/static/src/scss/health_dashboard.scss",
            "inom_server_health/static/src/js/health_dashboard.js",
            "inom_server_health/static/src/xml/health_dashboard.xml",
        ],
    },
    'images': ['static/description/banner.png'],
    "post_init_hook": "post_init_hook",
    "installable": True,
    "application": True,
}
