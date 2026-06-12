from odoo import models, fields


class EdmDashboard(models.Model):
    _name = 'edm.dashboard'
    _description = 'Document Dashboard'

    name = fields.Char(default='Dashboard')

    total_documents = fields.Integer(compute='_compute_counts')
    draft_documents = fields.Integer(compute='_compute_counts')
    waiting_documents = fields.Integer(compute='_compute_counts')
    approved_documents = fields.Integer(compute='_compute_counts')
    rejected_documents = fields.Integer(compute='_compute_counts')
    favorite_documents = fields.Integer(compute='_compute_counts')
    expired_documents = fields.Integer(compute='_compute_counts')
    expiring_soon_documents = fields.Integer(compute='_compute_counts')

    total_requests = fields.Integer(compute='_compute_counts')
    accepted_requests = fields.Integer(compute='_compute_counts')
    rejected_requests = fields.Integer(compute='_compute_counts')

    def _compute_counts(self):
        Document = self.env['edm.document'].sudo()
        Request = self.env['edm.document.request'].sudo()
        for rec in self:
            rec.total_documents = Document.search_count([('is_trashed', '=', False)])
            rec.draft_documents = Document.search_count([('state', '=', 'draft'), ('is_trashed', '=', False)])
            rec.waiting_documents = Document.search_count([('state', '=', 'waiting'), ('is_trashed', '=', False)])
            rec.approved_documents = Document.search_count([('state', '=', 'approved'), ('is_trashed', '=', False)])
            rec.rejected_documents = Document.search_count([('state', '=', 'rejected'), ('is_trashed', '=', False)])
            rec.favorite_documents = Document.search_count([('is_favorite', '=', True), ('is_trashed', '=', False)])
            rec.expired_documents = Document.search_count([('expiry_status', '=', 'expired'), ('is_trashed', '=', False)])
            rec.expiring_soon_documents = Document.search_count([('expiry_status', '=', 'expiring_soon'), ('is_trashed', '=', False)])
            rec.total_requests = Request.search_count([])
            rec.accepted_requests = Request.search_count([('state', '=', 'accepted')])
            rec.rejected_requests = Request.search_count([('state', '=', 'rejected')])

    def _open_documents(self, domain, title):
        return {
            'type': 'ir.actions.act_window',
            'name': title,
            'res_model': 'edm.document',
            'view_mode': 'kanban,list,form',
            'domain': domain,
            'target': 'current',
        }

    def _open_requests(self, domain, title):
        return {
            'type': 'ir.actions.act_window',
            'name': title,
            'res_model': 'edm.document.request',
            'view_mode': 'list,form',
            'domain': domain,
            'target': 'current',
        }

    def action_open_all_documents(self):
        return self._open_documents([('is_trashed', '=', False)], 'All Documents')

    def action_open_draft_documents(self):
        return self._open_documents([('state', '=', 'draft'), ('is_trashed', '=', False)], 'Draft Documents')

    def action_open_waiting_documents(self):
        return self._open_documents([('state', '=', 'waiting'), ('is_trashed', '=', False)], 'Waiting Approval Documents')

    def action_open_approved_documents(self):
        return self._open_documents([('state', '=', 'approved'), ('is_trashed', '=', False)], 'Approved Documents')

    def action_open_rejected_documents(self):
        return self._open_documents([('state', '=', 'rejected'), ('is_trashed', '=', False)], 'Rejected Documents')

    def action_open_favorite_documents(self):
        return self._open_documents([('is_favorite', '=', True), ('is_trashed', '=', False)], 'Favorite Documents')

    def action_open_expired_documents(self):
        return self._open_documents([('expiry_status', '=', 'expired'), ('is_trashed', '=', False)], 'Expired Documents')

    def action_open_expiring_soon_documents(self):
        return self._open_documents([('expiry_status', '=', 'expiring_soon'), ('is_trashed', '=', False)], 'Expiring Soon Documents')

    def action_open_all_requests(self):
        return self._open_requests([], 'All Requests')

    def action_open_accepted_requests(self):
        return self._open_requests([('state', '=', 'accepted')], 'Accepted Requests')

    def action_open_rejected_requests(self):
        return self._open_requests([('state', '=', 'rejected')], 'Rejected Requests')