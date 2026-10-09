from odoo import api, fields, models
from odoo.exceptions import AccessError, ValidationError


class InomCourse(models.Model):
    _name = 'inom.course'
    _description = 'Online Course'
    _inherit = ['inom.mixin']
    _order = 'name'

    name = fields.Char(required=True, tracking=True)
    code = fields.Char(required=True, size=16)
    subject_id = fields.Many2one('inom.subject', index=True, ondelete='set null')
    department_id = fields.Many2one('inom.department', required=True, index=True,
                                    ondelete='restrict')
    faculty_id = fields.Many2one('inom.faculty', string='Taught by', index=True,
                                 ondelete='set null')
    summary = fields.Text()
    duration_hours = fields.Float()

    lesson_ids = fields.One2many('inom.lesson', 'course_id', string='Lessons')
    assignment_ids = fields.One2many('inom.assignment', 'course_id', string='Assignments')
    lesson_count = fields.Integer(compute='_compute_counts', store=True)

    published = fields.Boolean(
        default=False, tracking=True, index=True,
        help='Draft courses are invisible to students. Enforced by a record '
             'rule, not by a filter on the list.')

    _code_uniq = models.Constraint(
        'UNIQUE(code, company_id)',
        'That course code is already in use.')

    @api.depends('lesson_ids')
    def _compute_counts(self):
        for rec in self:
            rec.lesson_count = len(rec.lesson_ids)

    def _inom_action_publish(self, payload=None):
        self.ensure_one()
        if not self.lesson_ids:
            raise ValidationError('Add at least one lesson before publishing.')
        self.published = True
        return {'published': True}

    def _inom_action_unpublish(self, payload=None):
        self.ensure_one()
        self.published = False
        return {'published': False}

    @api.model
    def _inom_portal_fields(self):
        return ['id', 'display_name', 'name', 'code', 'subject_id', 'department_id',
                'faculty_id', 'summary', 'duration_hours', 'lesson_count', 'published']


class InomLesson(models.Model):
    _name = 'inom.lesson'
    _description = 'Lesson'
    _inherit = ['inom.mixin']
    _order = 'course_id, sequence'

    course_id = fields.Many2one('inom.course', required=True, ondelete='cascade', index=True)
    sequence = fields.Integer(default=10)
    name = fields.Char(required=True)
    content_type = fields.Selection(
        [('video', 'Video'), ('document', 'Document'), ('link', 'External link'),
         ('text', 'Reading')],
        default='document', required=True)
    duration_minutes = fields.Integer()
    body = fields.Html(
        string='Reading',
        help='Shown in the lesson itself. Use this for a reading, notes, or '
             'anything that does not need a file.')
    url = fields.Char(
        string='Link',
        help='YouTube, Vimeo or a direct video URL for a video lesson; a PDF '
             'address for a document. Played or shown in the lesson rather '
             'than opened elsewhere.')
    file_data = fields.Binary(
        string='File', attachment=True,
        help='Upload the document here instead of linking to it. Up to 25 MB.')
    file_name = fields.Char()

    #: A lesson file can reasonably be a scanned book chapter.
    MAX_BYTES = 25 * 1024 * 1024

    @api.constrains('file_data')
    def _check_size(self):
        import base64
        for rec in self:
            if not rec.file_data:
                continue
            size = len(base64.b64decode(rec.file_data))
            if size > rec.MAX_BYTES:
                raise ValidationError(
                    f'That file is {size / 1024 / 1024:.1f} MB. The limit is '
                    f'{rec.MAX_BYTES // 1024 // 1024} MB.')

    @api.constrains('content_type', 'url', 'file_data', 'body')
    def _check_has_content(self):
        """A lesson with nothing in it is a title a student cannot open.

        Easy to create by accident — the name and type are enough to save —
        and it looks identical to a lesson that works until somebody clicks
        it.
        """
        for rec in self:
            if rec.content_type == 'text' and not rec.body:
                raise ValidationError(
                    f'"{rec.name}" is a reading with nothing to read. Write '
                    f'the text, or change the type.')
            if rec.content_type in ('video', 'link') and not rec.url:
                raise ValidationError(
                    f'"{rec.name}" needs a link. A {rec.content_type} lesson '
                    f'with no address is a title a student cannot open.')
            if rec.content_type == 'document' and not (rec.url or rec.file_data):
                raise ValidationError(
                    f'"{rec.name}" needs a file or a link to one.')

    def _inom_action_open(self, payload=None):
        """Open the lesson in the player.

        A workflow action rather than a link on the row: the client needs to
        know it is a lesson and not a record, and the registry is where that
        is declared. Returns nothing to write — this changes no data.
        """
        self.ensure_one()
        return {'open_lesson': self.id}

    def _inom_embed(self):
        """How the portal should show this lesson.

        Returned from the server rather than worked out in the browser: what
        can be embedded is a policy question — an institution may not want
        YouTube on its pages — and policy belongs where it can be changed
        without a release.
        """
        self.ensure_one()
        url = (self.url or '').strip()

        if self.content_type == 'text':
            return {'kind': 'text'}

        if self.file_data:
            return {'kind': 'pdf' if (self.file_name or '').lower().endswith('.pdf')
                    else 'file',
                    'src': f'/ums/lesson/{self.id}/file'}

        if not url:
            return {'kind': 'none'}

        # YouTube and Vimeo need their embed form; a watch URL in an iframe is
        # refused by their own headers and shows an empty box.
        import re
        youtube = re.search(
            r'(?:youtube\.com/(?:watch\?v=|embed/)|youtu\.be/)([\w-]{6,})', url)
        if youtube:
            return {'kind': 'iframe',
                    'src': f'https://www.youtube-nocookie.com/embed/{youtube.group(1)}'}

        vimeo = re.search(r'vimeo\.com/(?:video/)?(\d+)', url)
        if vimeo:
            return {'kind': 'iframe',
                    'src': f'https://player.vimeo.com/video/{vimeo.group(1)}'}

        if url.lower().split('?')[0].endswith(('.mp4', '.webm', '.ogg', '.m4v')):
            return {'kind': 'video', 'src': url}

        if url.lower().split('?')[0].endswith('.pdf'):
            return {'kind': 'pdf', 'src': url}

        # Anything else is opened rather than embedded. Framing an arbitrary
        # page usually fails silently on its X-Frame-Options, and a link that
        # works beats a blank rectangle that does not.
        return {'kind': 'link', 'src': url}

    @api.model
    def _inom_portal_fields(self):
        return ['id', 'display_name', 'course_id', 'sequence', 'name',
                'content_type', 'duration_minutes', 'url', 'body',
                'file_data', 'file_name']


class InomAssignment(models.Model):
    _name = 'inom.assignment'
    _description = 'Assignment'
    _inherit = ['inom.mixin']
    _order = 'due_on desc'

    name = fields.Char(required=True, tracking=True)
    course_id = fields.Many2one('inom.course', required=True, index=True,
                                ondelete='restrict')
    department_id = fields.Many2one(
        'inom.department', related='course_id.department_id', store=True, index=True,
        ondelete='set null')
    faculty_id = fields.Many2one(related='course_id.faculty_id', store=True, index=True,
                                 ondelete='set null')
    instructions = fields.Html()
    issued_on = fields.Date(default=fields.Date.context_today)
    due_on = fields.Date(required=True)
    max_marks = fields.Float(default=20.0, required=True)

    submission_ids = fields.One2many('inom.submission', 'assignment_id', string='Submissions')
    submitted_count = fields.Integer(compute='_compute_counts', store=True)
    graded_count = fields.Integer(compute='_compute_counts', store=True)

    @api.depends('submission_ids.state')
    def _compute_counts(self):
        for rec in self:
            rec.submitted_count = len(rec.submission_ids)
            rec.graded_count = len(rec.submission_ids.filtered(
                lambda s: s.state == 'graded'))

    @api.constrains('issued_on', 'due_on')
    def _check_dates(self):
        for rec in self:
            if rec.issued_on and rec.due_on < rec.issued_on:
                raise ValidationError('An assignment cannot be due before it is issued.')

    @api.model
    def _inom_portal_fields(self):
        return ['id', 'display_name', 'name', 'course_id', 'faculty_id',
                'issued_on', 'due_on', 'max_marks', 'submitted_count', 'graded_count']


class InomSubmission(models.Model):
    _name = 'inom.submission'
    _description = 'Assignment Submission'
    _inherit = ['inom.mixin']
    _order = 'submitted_on desc'
    _rec_name = 'display_name'
    _rec_names_search = ['student_id.name', 'student_id.enrolment_no',
                         'assignment_id.name']

    assignment_id = fields.Many2one('inom.assignment', required=True,
                                    ondelete='cascade', index=True)
    student_id = fields.Many2one('inom.student', required=True, index=True,
                                 ondelete='restrict')
    course_id = fields.Many2one(related='assignment_id.course_id', store=True, index=True,
                                ondelete='set null')
    department_id = fields.Many2one(related='assignment_id.department_id', store=True,
                                    index=True, ondelete='set null')

    submitted_on = fields.Datetime(default=fields.Datetime.now, required=True)
    late = fields.Boolean(compute='_compute_late', store=True)
    body = fields.Html()
    marks = fields.Float()
    max_marks = fields.Float(related='assignment_id.max_marks', store=True)
    feedback = fields.Text()

    state = fields.Selection(
        [('submitted', 'Submitted'), ('grading', 'Being graded'), ('graded', 'Graded'),
         ('returned', 'Returned for rework')],
        default='submitted', required=True, index=True, tracking=True)

    _submission_uniq = models.Constraint(
        'UNIQUE(assignment_id, student_id)',
        'That student has already submitted this assignment.')

    @api.depends('submitted_on', 'assignment_id.due_on')
    def _compute_late(self):
        for rec in self:
            due = rec.assignment_id.due_on
            rec.late = bool(due and rec.submitted_on and rec.submitted_on.date() > due)

    @api.constrains('marks', 'max_marks')
    def _check_marks(self):
        for rec in self:
            if rec.marks and rec.max_marks and rec.marks > rec.max_marks:
                raise ValidationError(
                    f'{rec.student_id.name} has {rec.marks} out of {rec.max_marks}.')

    @api.depends('student_id.name', 'assignment_id.name')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = f'{rec.student_id.name} · {rec.assignment_id.name}'

    def _inom_action_grade(self, payload=None):
        """Record a mark and feedback in one step.

        Feedback is required alongside the mark. A number with no explanation
        generates a query to the faculty member anyway, so it may as well be
        captured while they have the work in front of them.
        """
        self.ensure_one()
        marks = (payload or {}).get('marks')
        feedback = (payload or {}).get('feedback')
        if marks is None:
            raise ValidationError('Enter a mark.')
        if not feedback:
            raise ValidationError('Add a line of feedback with the mark.')
        self.write({'marks': float(marks), 'feedback': feedback, 'state': 'graded'})
        return {'state': 'graded'}

    def _inom_action_return_for_rework(self, payload=None):
        self.ensure_one()
        self.state = 'returned'
        return {'state': 'returned'}

    @api.model
    def _inom_portal_fields(self):
        return ['id', 'display_name', 'assignment_id', 'student_id', 'course_id',
                'submitted_on', 'late', 'marks', 'max_marks', 'feedback', 'state']


class InomSubmissionGuard(models.Model):
    """Students may write their own submission. Not their own mark.

    The record rule scopes a student to their own submission, and the ACL
    grants write so they can edit an answer before it is graded. Together those
    two correct-looking decisions let a student set `marks` on their own work
    through the generic write endpoint — the screen does not offer it, but the
    endpoint does not know that.

    Field-level authority has to be enforced on the model. A readonly flag in
    a view is a rendering instruction, not a permission.
    """
    _inherit = 'inom.submission'

    #: Only a grader may touch these.
    GRADER_FIELDS = {'marks', 'feedback', 'state'}

    def _inom_may_grade(self):
        user = self.env.user
        return (self.env.su
                or user.has_group('inom_base.group_inom_faculty')
                or user.has_group('inom_base.group_inom_hod')
                or user.has_group('inom_base.group_inom_dean')
                or user.has_group('inom_base.group_inom_registrar'))

    def write(self, vals):
        touched = self.GRADER_FIELDS & set(vals)
        if touched and not self._inom_may_grade():
            raise AccessError(
                'Only a grader can change a mark, feedback or the status of a '
                'submission.')
        if not self._inom_may_grade():
            graded = self.filtered(lambda s: s.state == 'graded')
            if graded:
                raise AccessError(
                    'This work has been graded and can no longer be edited. '
                    'Ask for it to be returned for rework if something is wrong.')
        return super().write(vals)

    @api.model_create_multi
    def create(self, vals_list):
        if not self._inom_may_grade():
            for vals in vals_list:
                # A student submitting cannot arrive pre-graded.
                for name in self.GRADER_FIELDS:
                    vals.pop(name, None)
        return super().create(vals_list)
