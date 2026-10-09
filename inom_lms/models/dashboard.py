from odoo import api, fields, models


class InomPortalDashboard(models.AbstractModel):
    _inherit = 'inom.portal.dashboard'

    @api.model
    def _dash_lms(self, scope):
        Course = self.env['inom.course']
        Assignment = self.env['inom.assignment']
        Submission = self.env['inom.submission']
        domain = self._scope_domain(scope, model='inom.submission')
        today = fields.Date.context_today(self)

        published = Course.search_count(domain + [('published', '=', True)])
        drafts = Course.search_count(domain + [('published', '=', False)])
        open_assignments = Assignment.search(domain + [('due_on', '>=', today)])
        ungraded = Submission.search_count(domain + [('state', '!=', 'graded')])
        late = Submission.search_count(domain + [('late', '=', True)])

        kpis = [
            self._kpi('Published courses', published),
            self._kpi('Drafts', drafts, tone='idle',
                      hint='Not visible to students.'),
            self._kpi('Assignments open', len(open_assignments)),
            self._kpi('Awaiting grading', ungraded, tone='warn' if ungraded else 'ok'),
        ]

        cards = [
            {'cols': 2, 'items': [
                {'title': 'Courses by department', 'type': 'hbar',
                 'values': [{'label': label, 'value': count} for label, count in
                            sorted(self._group_counts('inom.course', domain, 'department_id'),
                                   key=lambda r: -r[1])[:10]]},
                {'title': 'Submissions by stage', 'type': 'donut',
                 'values': [{'label': label, 'value': count} for label, count in
                            self._group_counts('inom.submission', domain, 'state')]},
            ]},
            {'cols': 1, 'items': [
                {'title': 'Assignments closing soon', 'type': 'table',
                 'head': ['Assignment', 'Course', 'Due', 'Submitted', 'Graded'],
                 'rows': [[a.name, a.course_id.code, str(a.due_on),
                           a.submitted_count, a.graded_count]
                          for a in open_assignments.sorted('due_on')[:12]]},
                {'title': 'Late submissions', 'type': 'note',
                 'text': f'{late} submissions arrived after their due date.'},
            ]},
        ]
        return {'kpis': kpis, 'cards': cards}
