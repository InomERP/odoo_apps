"""Courses and lessons: publishing, content checks and embedding.

Run with:

    odoo -d <db> --test-enable --test-tags inom_lms --stop-after-init
"""
from odoo.exceptions import ValidationError
from odoo.tests import tagged

from .common import InomLmsCommon


@tagged('post_install', '-at_install', 'inom_lms')
class TestCourse(InomLmsCommon):

    def test_publish_requires_a_lesson(self):
        with self.assertRaises(ValidationError):
            self.course._inom_action_publish()
        self.assertFalse(self.course.published)

    def test_publish_and_unpublish(self):
        self._lesson()
        self.assertEqual(self.course._inom_action_publish(), {'published': True})
        self.assertTrue(self.course.published)
        self.assertEqual(self.course._inom_action_unpublish(), {'published': False})
        self.assertFalse(self.course.published)

    def test_lesson_count(self):
        self._lesson(name='One')
        self._lesson(name='Two')
        self.assertEqual(self.course.lesson_count, 2)

    def test_empty_lessons_refused(self):
        with self.assertRaises(ValidationError):
            self._lesson(content_type='text', url=False, body=False)
        with self.assertRaises(ValidationError):
            self._lesson(content_type='video', url=False)
        with self.assertRaises(ValidationError):
            self._lesson(content_type='document', url=False)

    def test_embed_kinds(self):
        cases = [
            ('video', 'https://www.youtube.com/watch?v=abcdef123', 'iframe',
             'https://www.youtube-nocookie.com/embed/abcdef123'),
            ('video', 'https://vimeo.com/123456', 'iframe',
             'https://player.vimeo.com/video/123456'),
            ('video', 'https://cdn.example.com/clip.mp4', 'video',
             'https://cdn.example.com/clip.mp4'),
            ('document', 'https://example.com/notes.pdf', 'pdf',
             'https://example.com/notes.pdf'),
            ('link', 'https://example.com/page', 'link', 'https://example.com/page'),
        ]
        for content_type, url, kind, src in cases:
            lesson = self._lesson(content_type=content_type, url=url)
            self.assertEqual(lesson._inom_embed(), {'kind': kind, 'src': src}, url)
        reading = self._lesson(content_type='text', url=False, body='<p>Read me</p>')
        self.assertEqual(reading._inom_embed(), {'kind': 'text'})

    def test_open_action(self):
        lesson = self._lesson()
        self.assertEqual(lesson._inom_action_open(), {'open_lesson': lesson.id})
