# -*- coding: utf-8 -*-
"""
Dashboard data controller for the Advanced DMS module.

This controller is ADDITIVE. It only reads existing data from the
`edm.document` / `edm.document.request` models and returns aggregated
KPIs and chart datasets for the OWL analytics dashboard. It does not
modify any existing business logic.
"""

from collections import OrderedDict
from datetime import date, datetime, timedelta

import base64

from odoo import fields, http
from odoo.http import request
from werkzeug.exceptions import NotFound


class EdmDashboardController(http.Controller):

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _human_size(num_bytes):
        """Return a human readable representation of a byte count."""
        if not num_bytes:
            return "0 B"
        units = ["B", "KB", "MB", "GB", "TB"]
        size = float(num_bytes)
        for unit in units:
            if size < 1024.0 or unit == units[-1]:
                if unit == "B":
                    return "%d %s" % (int(size), unit)
                return "%.1f %s" % (size, unit)
            size /= 1024.0
        return "%.1f TB" % size

    # ------------------------------------------------------------------
    # Folder contents endpoint (in-dashboard folder navigation)
    # ------------------------------------------------------------------
    @http.route(['/edm/document/preview/<int:document_id>'], type='http', auth='user')
    def edm_document_preview(self, document_id, **kw):
        """Serve a document inline with its real filename so the PDF viewer
        shows the document name instead of '(anonymous)'. Reads with the
        caller's own rights so record rules apply."""
        document = request.env['edm.document'].browse(document_id)
        if not document.exists() or not document.file:
            raise NotFound()
        filecontent = base64.b64decode(document.file)
        ext = (document.file_extension or '').lower()
        filename = document.file_name or document.name or 'document'
        if ext and not filename.lower().endswith('.' + ext):
            filename = '%s.%s' % (filename, ext)
        mimetype = 'application/pdf' if ext == 'pdf' else 'application/octet-stream'
        return request.make_response(
            filecontent,
            headers=[
                ('Content-Type', mimetype),
                ('Content-Disposition', "inline; filename=\"%s\"" % filename),
            ]
        )

    @http.route(
        "/edm/dashboard/folder",
        type="jsonrpc",
        auth="user",
        methods=["POST"],
        csrf=False,
    )
    def folder_contents(self, folder_id=None, **kw):
        """Return the subfolders and documents inside a folder.

        ``folder_id`` may be ``None`` (or falsy) to list the root level.
        Records are read with the caller's own rights so access rules apply.
        """
        Document = request.env["edm.document"]
        Folder = request.env["edm.folder"]

        base_domain = [("is_trashed", "=", False)]

        if folder_id:
            folder_id = int(folder_id)
            subfolder_recs = Folder.search(
                [("parent_id", "=", folder_id)], order="name"
            )
            doc_recs = Document.search(
                base_domain + [("folder_id", "=", folder_id)], order="name"
            )
        else:
            subfolder_recs = Folder.search(
                [("parent_id", "=", False)], order="name"
            )
            doc_recs = Document.search(
                base_domain + [("folder_id", "=", False)], order="name"
            )

        # Document counts for the subfolders shown.
        sub_count_map = {}
        if subfolder_recs:
            sub_groups = Document.sudo()._read_group(
                base_domain + [("folder_id", "in", subfolder_recs.ids)],
                groupby=["folder_id"],
                aggregates=["__count"],
            )
            sub_count_map = {f.id: c for f, c in sub_groups}

        subfolders = [
            {
                "id": f.id,
                "name": f.name,
                "count": sub_count_map.get(f.id, 0),
            }
            for f in subfolder_recs
        ]

        documents = []
        for doc in doc_recs:
            ext = (doc.file_extension or "").lower()
            documents.append(
                {
                    "id": doc.id,
                    "name": doc.name,
                    "extension": ext or "file",
                    "is_pdf": ext == "pdf" and bool(doc.file),
                    "state": doc.state or "draft",
                    "owner": doc.owner_id.name if doc.owner_id else "",
                    "is_favorite": bool(doc.is_favorite),
                }
            )

        # Build the breadcrumb trail from the root down to the current folder.
        breadcrumb = []
        if folder_id:
            node = Folder.browse(folder_id)
            guard = 0
            while node and guard < 50:
                breadcrumb.insert(0, {"id": node.id, "name": node.name})
                node = node.parent_id
                guard += 1

        return {
            "status": "ok",
            "folder_id": folder_id or False,
            "subfolders": subfolders,
            "documents": documents,
            "breadcrumb": breadcrumb,
        }

    # ------------------------------------------------------------------
    # Main dashboard data endpoint
    # ------------------------------------------------------------------
    @http.route(
        "/edm/dashboard/data",
        type="jsonrpc",
        auth="user",
        methods=["POST"],
        csrf=False,
    )
    def dashboard_data(self, date_from=None, date_to=None, **kw):
        """Return all KPIs + chart datasets in a single round trip.

        Optional ``date_from`` / ``date_to`` (YYYY-MM-DD strings) restrict
        the document based statistics to a creation-date window.
        """
        Document = request.env["edm.document"].sudo()
        Request = request.env["edm.document.request"].sudo()
        Attachment = request.env["ir.attachment"].sudo()

        # --- Resolve the optional date range -------------------------------
        base_domain = [("is_trashed", "=", False)]
        range_domain = list(base_domain)
        if date_from:
            range_domain.append(("create_date", ">=", "%s 00:00:00" % date_from))
        if date_to:
            range_domain.append(("create_date", "<=", "%s 23:59:59" % date_to))

        today = fields.Date.today()
        today_start = "%s 00:00:00" % today

        # --- KPI cards -----------------------------------------------------
        total_documents = Document.search_count(range_domain)
        uploaded_today = Document.search_count(
            base_domain + [("create_date", ">=", today_start)]
        )
        approved_documents = Document.search_count(
            range_domain + [("state", "=", "approved")]
        )
        rejected_documents = Document.search_count(
            range_domain + [("state", "=", "rejected")]
        )
        expired_documents = Document.search_count(
            range_domain + [("expiry_status", "=", "expired")]
        )
        pending_requests = Request.search_count([("state", "=", "requested")])

        # Storage usage: read real attachment sizes for stored binaries.
        storage_bytes = 0
        attachments = Attachment.search_read(
            [("res_model", "=", "edm.document")],
            ["file_size"],
        )
        for att in attachments:
            storage_bytes += att.get("file_size") or 0

        # Active users: distinct owners of non-trashed documents.
        owner_rows = Document._read_group(
            base_domain + [("owner_id", "!=", False)],
            groupby=["owner_id"],
            aggregates=["__count"],
        )
        active_users = len(owner_rows)

        kpis = {
            "total_documents": total_documents,
            "uploaded_today": uploaded_today,
            "pending_requests": pending_requests,
            "approved_documents": approved_documents,
            "rejected_documents": rejected_documents,
            "expired_documents": expired_documents,
            "storage_usage": self._human_size(storage_bytes),
            "storage_bytes": storage_bytes,
            "active_users": active_users,
        }

        # --- Chart: upload trend (last 30 days) ----------------------------
        trend_days = 30
        trend_labels = []
        trend_counts = []
        for offset in range(trend_days - 1, -1, -1):
            day = today - timedelta(days=offset)
            day_start = "%s 00:00:00" % day
            day_end = "%s 23:59:59" % day
            count = Document.search_count(
                base_domain
                + [("create_date", ">=", day_start), ("create_date", "<=", day_end)]
            )
            trend_labels.append(day.strftime("%d %b"))
            trend_counts.append(count)

        # --- Chart: monthly statistics (last 12 months) --------------------
        month_labels = []
        month_counts = []
        first_of_month = today.replace(day=1)
        months = []
        cursor = first_of_month
        for _ in range(12):
            months.append(cursor)
            # step back one month
            prev_month_last_day = cursor - timedelta(days=1)
            cursor = prev_month_last_day.replace(day=1)
        for month_start in reversed(months):
            if month_start.month == 12:
                next_month = month_start.replace(year=month_start.year + 1, month=1)
            else:
                next_month = month_start.replace(month=month_start.month + 1)
            month_end = next_month - timedelta(days=1)
            count = Document.search_count(
                base_domain
                + [
                    ("create_date", ">=", "%s 00:00:00" % month_start),
                    ("create_date", "<=", "%s 23:59:59" % month_end),
                ]
            )
            month_labels.append(month_start.strftime("%b %Y"))
            month_counts.append(count)

        # --- Chart: status distribution ------------------------------------
        status_map = OrderedDict(
            [
                ("draft", "Draft"),
                ("waiting", "Waiting"),
                ("approved", "Approved"),
                ("rejected", "Rejected"),
            ]
        )
        status_labels = list(status_map.values())
        status_counts = [
            Document.search_count(range_domain + [("state", "=", key)])
            for key in status_map.keys()
        ]

        # --- Chart: user activity (top 8 owners) ---------------------------
        user_rows = Document._read_group(
            range_domain + [("owner_id", "!=", False)],
            groupby=["owner_id"],
            aggregates=["__count"],
            order="__count desc",
            limit=8,
        )
        user_labels = [owner.name for owner, _count in user_rows]
        user_counts = [count for _owner, count in user_rows]

        # --- Chart: documents grouped by workspace (department analog) -----
        ws_rows = Document._read_group(
            range_domain + [("workspace_id", "!=", False)],
            groupby=["workspace_id"],
            aggregates=["__count"],
            order="__count desc",
            limit=10,
        )
        ws_labels = [ws.name for ws, _count in ws_rows]
        ws_counts = [count for _ws, count in ws_rows]

        charts = {
            "upload_trend": {"labels": trend_labels, "data": trend_counts},
            "monthly": {"labels": month_labels, "data": month_counts},
            "status": {"labels": status_labels, "data": status_counts},
            "user_activity": {"labels": user_labels, "data": user_counts},
            "workspace": {"labels": ws_labels, "data": ws_counts},
        }

        # --- Recent / latest uploaded documents ----------------------------
        recent = Document.search_read(
            range_domain,
            ["id", "name", "file_extension", "state", "owner_id", "create_date"],
            limit=8,
            order="create_date desc",
        )
        latest_documents = []
        for doc in recent:
            create_date = doc.get("create_date")
            if create_date:
                if isinstance(create_date, str):
                    create_date_str = create_date
                else:
                    create_date_str = fields.Datetime.to_string(create_date)
            else:
                create_date_str = ""
            latest_documents.append(
                {
                    "id": doc["id"],
                    "name": doc["name"],
                    "extension": doc.get("file_extension") or "file",
                    "state": doc.get("state") or "draft",
                    "owner": doc["owner_id"][1] if doc.get("owner_id") else "",
                    "create_date": create_date_str,
                }
            )

        # --- User-centric summary cards -----------------------------------
        uid = request.env.uid
        my_documents = Document.search_count(
            base_domain + [("owner_id", "=", uid)]
        )
        shared_with_me = Document.search_count(
            base_domain
            + [("allowed_user_ids", "in", [uid]), ("owner_id", "!=", uid)]
        )
        need_my_review = Request.search_count(
            [("requested_to", "=", uid), ("state", "=", "requested")]
        )
        pending_with_others = Request.search_count(
            [("requested_by", "=", uid), ("state", "=", "requested")]
        )
        stats = {
            "my_documents": my_documents,
            "shared_with_me": shared_with_me,
            "need_my_review": need_my_review,
            "pending_with_others": pending_with_others,
        }

        # --- Folders with their (non-trashed) document counts --------------
        Folder = request.env["edm.folder"].sudo()
        folder_groups = Document._read_group(
            base_domain + [("folder_id", "!=", False)],
            groupby=["folder_id"],
            aggregates=["__count"],
        )
        folder_count_map = {
            folder.id: count for folder, count in folder_groups
        }
        folder_recs = Folder.search([], order="name", limit=100)
        folders = [
            {
                "id": folder.id,
                "name": folder.name,
                "count": folder_count_map.get(folder.id, 0),
            }
            for folder in folder_recs
        ]

        # --- Storage usage widget ------------------------------------------
        # Default soft quota; adjust to your deployment policy if required.
        default_quota_bytes = 15 * 1024 * 1024 * 1024  # 15 GB
        storage_percent = 0.0
        if default_quota_bytes:
            storage_percent = round(
                min(storage_bytes / default_quota_bytes * 100.0, 100.0), 1
            )
        storage = {
            "used_bytes": storage_bytes,
            "used_human": self._human_size(storage_bytes),
            "quota_human": self._human_size(default_quota_bytes),
            "percent": storage_percent,
        }

        return {
            "status": "ok",
            "kpis": kpis,
            "charts": charts,
            "latest_documents": latest_documents,
            "stats": stats,
            "folders": folders,
            "storage": storage,
        }
