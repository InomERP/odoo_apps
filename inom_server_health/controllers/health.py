# -*- coding: utf-8 -*-
import logging
from datetime import timedelta, timezone

from odoo import fields, http
from odoo.exceptions import AccessError
from odoo.http import request

from ..tools.collector import collect

_logger = logging.getLogger(__name__)

# How far back the trace opens. Points are returned with their timestamps --
# the client plots against time, not index, so a coarse 1-minute history and a
# fine 10-second live feed can share one axis honestly.
SEED_MINUTES = 60
SEED_POINTS = 400


class ServerHealthController(http.Controller):

    def _guard(self):
        """Both endpoints expose infrastructure detail -- process list, mount
        points, connection counts. Never public, never plain internal user.
        """
        if not request.env.user.has_group(
                "inom_server_health.group_server_health_viewer"):
            raise AccessError(
                "Server health metrics require the Server Health / Viewer "
                "access group.")

    # Deliberately type='http' + make_json_response rather than type='json'.
    # Odoo 18 renamed the JSON route type to 'jsonrpc'; this form works
    # unchanged on 17, 18 and 19 and avoids the RPC envelope overhead.
    @http.route("/inom_server_health/live", type="http", auth="user",
                methods=["GET"], csrf=False, save_session=False)
    def live(self, **kwargs):
        """Live metrics. Read-only, group-gated, never public.

        save_session=False matters: without it every poll rewrites the session
        file, which on a timer is a needless write storm.
        """
        self._guard()
        try:
            payload = collect(request.env.cr)
            self._resolve_user_names(payload)
        except Exception:
            _logger.exception("Server health collection failed")
            return request.make_json_response(
                {"error": "collection_failed"}, status=500)
        return request.make_json_response(payload)

    def _resolve_user_names(self, payload):
        """Names come through the ORM, not the raw probe.

        The probe returns ids only; reading display_name here keeps record
        rules and access checks in play rather than bypassing them with a
        join in SQL.
        """
        users = (payload.get("odoo") or {}).get("users") or {}
        rows = users.pop("rows", None)
        if not rows:
            users.setdefault("users", [])
            return
        records = request.env["res.users"].browse(
            [r["user_id"] for r in rows]).exists()
        names = {u.id: u.display_name for u in records}
        users["users"] = [{
            "id": r["user_id"],
            "name": names.get(r["user_id"], "?"),
            "status": r["status"],
            "idle_s": int(r.get("idle_s") or 0),
        } for r in rows if r["user_id"] in names]
        users.pop("user_ids", None)

    @http.route("/inom_server_health/seed", type="http", auth="user",
                methods=["GET"], csrf=False, save_session=False)
    def seed(self, **kwargs):
        """Recent cron-captured samples, so the trace opens mid-flight
        instead of drawing itself from an empty canvas.

        Called once on mount. Never on the poll path.
        """
        self._guard()
        cutoff = fields.Datetime.now() - timedelta(minutes=SEED_MINUTES)
        samples = request.env["inom.server.health.sample"].search_read(
            [("sampled_at", ">=", cutoff)],
            ["sampled_at", "cpu_percent", "memory_percent",
             "pg_conn_percent", "load_1m"],
            order="sampled_at desc", limit=SEED_POINTS)
        samples.reverse()
        return request.make_json_response({
            "window_minutes": SEED_MINUTES,
            "points": [{
                # Epoch milliseconds. sampled_at is naive UTC.
                "t": int(s["sampled_at"].replace(
                    tzinfo=timezone.utc).timestamp() * 1000),
                "cpu": s["cpu_percent"],
                "mem": s["memory_percent"],
                "db": s["pg_conn_percent"],
                # load_1m is absolute; the trace is a percentage plot, so
                # normalise against the core allowance client-side.
                "load_raw": s["load_1m"],
            } for s in samples],
        })
