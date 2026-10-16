from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient
from io import StringIO

from accounts.models import Profile
from courses.educator_forms import AnnotationForm, CourseForm, LessonForm
from courses.models import Annotation, Course, Lesson, StudentProgress
from courses.permissions import IsCourseOwner


def _make_educator(username):
    user = User.objects.create_user(username, password="pass12345")
    profile = Profile.objects.get(user=user)
    profile.role = Profile.Role.EDUCATOR
    profile.save(update_fields=["role"])
    return user


class LessonOrderValidationTests(TestCase):
    def setUp(self):
        self.educator = _make_educator("teacher")
        self.course = Course.objects.create(
            title="Anatomy",
            description="Demo",
            owner=self.educator,
        )
        Lesson.objects.create(
            course=self.course,
            title="Intro",
            description="First",
            order=1,
        )

    def test_lesson_form_rejects_duplicate_order(self):
        form = LessonForm(
            data={
                "title": "Duplicate order",
                "description": "Should fail",
                "order": 1,
                "interaction_guide": "",
            },
            course=self.course,
        )
        self.assertFalse(form.is_valid())
        self.assertIn("order", form.errors)

    def test_lesson_create_view_returns_form_errors_not_500(self):
        self.client.force_login(self.educator)
        response = self.client.post(
            reverse("educator_lesson_create", args=[self.course.id]),
            {
                "title": "Another",
                "description": "Dup order",
                "order": 1,
                "interaction_guide": "",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "already exists")
        self.assertEqual(Lesson.objects.filter(course=self.course).count(), 1)

    def test_educator_lesson_api_rejects_duplicate_order(self):
        client = APIClient()
        client.force_authenticate(user=self.educator)
        response = client.post(
            "/api/educator/lessons/",
            {
                "course": self.course.id,
                "title": "Another",
                "description": "Dup order",
                "order": 1,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("order", response.data)
        self.assertEqual(Lesson.objects.filter(course=self.course).count(), 1)


class ViewerProgressTests(TestCase):
    def setUp(self):
        self.student = User.objects.create_user("learner", password="pass12345")
        self.course = Course.objects.create(title="Course", description="Desc")
        self.lesson = Lesson.objects.create(
            course=self.course,
            title="Lesson",
            description="Body",
            order=1,
        )

    def test_viewer_get_does_not_create_progress(self):
        self.client.force_login(self.student)
        before = StudentProgress.objects.count()
        response = self.client.get(reverse("lesson_viewer", args=[self.lesson.id]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(StudentProgress.objects.count(), before)

    def test_mark_complete_creates_progress(self):
        self.client.force_login(self.student)
        response = self.client.post(
            reverse("api-lesson-complete", args=[self.lesson.id]),
            data={"action": "complete"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            StudentProgress.objects.filter(
                student=self.student,
                lesson=self.lesson,
                completed=True,
            ).exists()
        )

    def test_get_or_create_for_is_idempotent(self):
        first, created_first = StudentProgress.get_or_create_for(
            self.student, self.lesson
        )
        second, created_second = StudentProgress.get_or_create_for(
            self.student, self.lesson
        )
        self.assertTrue(created_first)
        self.assertFalse(created_second)
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(
            StudentProgress.objects.filter(
                student=self.student, lesson=self.lesson
            ).count(),
            1,
        )

    def test_html_mark_complete_rejects_unknown_action(self):
        self.client.force_login(self.student)
        response = self.client.post(
            reverse("mark_complete", args=[self.lesson.id]),
            {"action": "nope"},
        )
        self.assertEqual(response.status_code, 302)
        progress = StudentProgress.objects.get(
            student=self.student, lesson=self.lesson
        )
        self.assertFalse(progress.completed)


class SeedDemoCommandTests(TestCase):
    @override_settings(DEBUG=False)
    def test_seed_demo_refuses_when_not_debug(self):
        with self.assertRaises(CommandError):
            call_command("seed_demo", stdout=StringIO())

    @override_settings(DEBUG=True)
    def test_seed_demo_runs_in_debug(self):
        out = StringIO()
        call_command("seed_demo", stdout=out)
        self.assertIn("Demo data ready", out.getvalue())
        self.assertTrue(Course.objects.filter(title="Demo: Explore a Box").exists())


class CourseDetailProgressTests(TestCase):
    def setUp(self):
        self.student = User.objects.create_user("cd_student", password="pass12345")
        self.course = Course.objects.create(title="Detail Course", description="d")
        self.l1 = Lesson.objects.create(
            course=self.course, title="L1", description="d", order=1
        )
        Lesson.objects.create(
            course=self.course, title="L2", description="d", order=2
        )
        StudentProgress.objects.create(
            student=self.student, lesson=self.l1, completed=True
        )

    def test_course_detail_uses_loaded_progress(self):
        self.client.force_login(self.student)
        response = self.client.get(reverse("course_detail", args=[self.course.id]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["progress"]["total"], 2)
        self.assertEqual(response.context["progress"]["completed"], 1)
        self.assertEqual(response.context["progress"]["percent"], 50)


class PermissionTests(TestCase):
    def test_is_course_owner_requires_authentication(self):
        from django.contrib.auth.models import AnonymousUser
        from django.test import RequestFactory

        request = RequestFactory().get("/")
        request.user = AnonymousUser()
        self.assertFalse(IsCourseOwner().has_permission(request, None))

        request.user = User.objects.create_user("authed", password="x")
        self.assertTrue(IsCourseOwner().has_permission(request, None))


class AnnotationOrderValidationTests(TestCase):
    def setUp(self):
        self.course = Course.objects.create(title="C", description="d")
        self.lesson = Lesson.objects.create(
            course=self.course, title="L", description="d", order=1
        )
        Annotation.objects.create(
            lesson=self.lesson,
            title="A",
            description="",
            position_x=0,
            position_y=0,
            position_z=0,
            order=1,
        )

    def test_annotation_form_rejects_duplicate_order(self):
        form = AnnotationForm(
            data={
                "title": "B",
                "description": "",
                "position_x": 1,
                "position_y": 1,
                "position_z": 1,
                "order": 1,
            },
            lesson=self.lesson,
        )
        self.assertFalse(form.is_valid())
        self.assertIn("order", form.errors)


class UploadSizeValidationTests(TestCase):
    @override_settings(MAX_LESSON_MODEL_BYTES=10, MAX_COURSE_THUMBNAIL_BYTES=10)
    def test_lesson_form_rejects_oversized_model(self):
        form = LessonForm(
            data={
                "title": "Big model",
                "description": "Desc",
                "order": 1,
                "interaction_guide": "",
            },
            files={
                "model_file": SimpleUploadedFile(
                    "big.glb",
                    b"01234567890123456789",
                    content_type="model/gltf-binary",
                )
            },
            course=Course(title="tmp", description="d"),
        )
        self.assertFalse(form.is_valid())
        self.assertIn("model_file", form.errors)

    @override_settings(MAX_COURSE_THUMBNAIL_BYTES=10)
    def test_course_form_rejects_oversized_thumbnail(self):
        form = CourseForm(
            data={"title": "Course", "description": "Desc"},
            files={
                "thumbnail": SimpleUploadedFile(
                    "big.jpg",
                    b"01234567890123456789",
                    content_type="image/jpeg",
                )
            },
        )
        self.assertFalse(form.is_valid())
        self.assertIn("thumbnail", form.errors)


class QueryBudgetTests(TestCase):
    def setUp(self):
        self.educator = _make_educator("ed")
        self.student = User.objects.create_user("st", password="pass12345")
        for i in range(5):
            course = Course.objects.create(
                title=f"Course {i}",
                description="Desc",
                owner=self.educator,
            )
            for order in (1, 2):
                Lesson.objects.create(
                    course=course,
                    title=f"L{order}",
                    description="Body",
                    order=order,
                )

    def test_educator_dashboard_query_count_stays_flat(self):
        self.client.force_login(self.educator)
        with self.assertNumQueries(8):
            response = self.client.get(reverse("educator_dashboard"))
        self.assertEqual(response.status_code, 200)

    def test_profile_query_count_does_not_scale_with_progress_for(self):
        self.client.force_login(self.student)
        # Annotated course list — not 2 queries per course via progress_for().
        with self.assertNumQueries(5):
            response = self.client.get(reverse("profile"))
        self.assertEqual(response.status_code, 200)
