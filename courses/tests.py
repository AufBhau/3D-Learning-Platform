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


class ProductionServingTests(TestCase):
    def test_whitenoise_and_proxy_ssl_configured(self):
        from django.conf import settings

        self.assertIn(
            "whitenoise.middleware.WhiteNoiseMiddleware", settings.MIDDLEWARE
        )
        self.assertEqual(
            settings.SECURE_PROXY_SSL_HEADER,
            ("HTTP_X_FORWARDED_PROTO", "https"),
        )
        self.assertTrue(settings.SERVE_MEDIA)

    def test_media_url_serves_uploaded_file(self):
        from django.conf import settings
        from pathlib import Path

        media_dir = Path(settings.MEDIA_ROOT) / "3d_models"
        media_dir.mkdir(parents=True, exist_ok=True)
        target = media_dir / "serve_probe.glb"
        target.write_bytes(b"glTF\x02\x00\x00\x00probe")
        try:
            response = self.client.get("/media/3d_models/serve_probe.glb")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(b"".join(response.streaming_content), target.read_bytes())
        finally:
            if target.exists():
                target.unlink()


class PublicApiTests(TestCase):
    def setUp(self):
        self.course = Course.objects.create(title="API Course", description="d")
        self.lesson = Lesson.objects.create(
            course=self.course, title="API Lesson", description="d", order=1
        )

    def test_course_list_and_lesson_detail(self):
        list_resp = self.client.get("/api/courses/")
        self.assertEqual(list_resp.status_code, 200)
        self.assertTrue(any(row["id"] == self.course.id for row in list_resp.json()))

        detail = self.client.get(f"/api/lessons/{self.lesson.id}/")
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.json()["title"], "API Lesson")
        self.assertIn("camera_zoom", detail.json())


class CrossTenantEducatorApiTests(TestCase):
    def setUp(self):
        self.owner = _make_educator("owner_ed")
        self.other = _make_educator("other_ed")
        self.course = Course.objects.create(
            title="Owner Course", description="d", owner=self.owner
        )
        self.lesson = Lesson.objects.create(
            course=self.course, title="Owned Lesson", description="d", order=1
        )
        self.hotspot = Annotation.objects.create(
            lesson=self.lesson,
            title="Spot",
            description="",
            position_x=0,
            position_y=0,
            position_z=0,
            order=1,
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.other)

    def test_cannot_retrieve_or_update_foreign_course(self):
        response = self.client.get(f"/api/educator/courses/{self.course.id}/")
        self.assertEqual(response.status_code, 404)

        response = self.client.patch(
            f"/api/educator/courses/{self.course.id}/",
            {"title": "Hijacked"},
            format="json",
        )
        self.assertEqual(response.status_code, 404)
        self.course.refresh_from_db()
        self.assertEqual(self.course.title, "Owner Course")

    def test_cannot_add_lesson_to_foreign_course(self):
        response = self.client.post(
            "/api/educator/lessons/",
            {
                "course": self.course.id,
                "title": "Intruder",
                "description": "nope",
                "order": 2,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("course", response.data)
        self.assertFalse(
            Lesson.objects.filter(course=self.course, title="Intruder").exists()
        )

    def test_cannot_touch_foreign_annotation(self):
        response = self.client.get(
            f"/api/educator/annotations/{self.hotspot.id}/"
        )
        self.assertEqual(response.status_code, 404)


class CameraAndModelValidationTests(TestCase):
    def setUp(self):
        self.educator = _make_educator("cam_ed")
        self.course = Course.objects.create(
            title="Cam Course", description="d", owner=self.educator
        )
        self.api = APIClient()
        self.api.force_authenticate(user=self.educator)

    def test_serializer_rejects_nan_camera_zoom(self):
        from courses.serializers import EducatorLessonSerializer

        serializer = EducatorLessonSerializer(
            data={
                "course": self.course.id,
                "title": "Bad zoom",
                "description": "d",
                "order": 1,
                "camera_distance_factor": float("nan"),
            },
            context={"request": type("R", (), {"user": self.educator})()},
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("camera_distance_factor", serializer.errors)

    def test_serializer_rejects_non_positive_camera_zoom(self):
        response = self.api.post(
            "/api/educator/lessons/",
            {
                "course": self.course.id,
                "title": "Neg zoom",
                "description": "d",
                "order": 1,
                "camera_distance_factor": -1,
                "camera_min_distance_factor": 0.25,
                "camera_max_distance_factor": 6,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("camera_distance_factor", response.data)

    def test_rejects_html_disguised_as_glb(self):
        form = LessonForm(
            data={
                "title": "Evil",
                "description": "d",
                "order": 1,
                "interaction_guide": "",
                "model_rotation_x": 0,
                "model_rotation_y": 0,
                "model_rotation_z": 0,
                "camera_distance_factor": 1,
                "camera_min_distance_factor": 0.25,
                "camera_max_distance_factor": 6,
            },
            files={
                "model_file": SimpleUploadedFile(
                    "evil.glb",
                    b"<html><script>alert(1)</script></html>",
                    content_type="model/gltf-binary",
                )
            },
            course=self.course,
        )
        self.assertFalse(form.is_valid())
        self.assertIn("model_file", form.errors)

    def test_accepts_glb_magic_header(self):
        form = LessonForm(
            data={
                "title": "Good",
                "description": "d",
                "order": 1,
                "interaction_guide": "",
                "model_rotation_x": 0,
                "model_rotation_y": 0,
                "model_rotation_z": 0,
                "camera_distance_factor": 1,
                "camera_min_distance_factor": 0.25,
                "camera_max_distance_factor": 6,
            },
            files={
                "model_file": SimpleUploadedFile(
                    "ok.glb",
                    b"glTF" + b"\x00" * 20,
                    content_type="model/gltf-binary",
                )
            },
            course=self.course,
        )
        self.assertTrue(form.is_valid(), form.errors)


class ApiThrottleTests(TestCase):
    def test_anon_api_returns_429_when_rate_exceeded(self):
        from unittest.mock import patch

        from django.core.cache import cache
        from rest_framework.throttling import AnonRateThrottle

        from courses.api_views import CourseListAPIView

        class BurstThrottle(AnonRateThrottle):
            rate = "2/min"

        # Earlier tests also call the API as anonymous. Throttle history
        # lives in the process-wide cache, so start this check from empty.
        cache.clear()
        Course.objects.create(title="T", description="d")
        with patch.object(CourseListAPIView, "throttle_classes", [BurstThrottle]):
            self.assertEqual(self.client.get("/api/courses/").status_code, 200)
            self.assertEqual(self.client.get("/api/courses/").status_code, 200)
            self.assertEqual(self.client.get("/api/courses/").status_code, 429)


class AnnotationCoordinateValidationTests(TestCase):
    def setUp(self):
        self.educator = _make_educator("anno_ed")
        self.course = Course.objects.create(
            title="Anno Course", description="d", owner=self.educator
        )
        self.lesson = Lesson.objects.create(
            course=self.course, title="L", description="d", order=1
        )
        self.api = APIClient()
        self.api.force_authenticate(user=self.educator)

    def test_educator_api_rejects_infinite_coordinate(self):
        response = self.api.post(
            "/api/educator/annotations/",
            {
                "lesson": self.lesson.id,
                "title": "Broken",
                "description": "",
                "x": "inf",
                "y": 0,
                "z": 0,
                "order": 1,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("x", response.data)
        self.assertFalse(
            Annotation.objects.filter(lesson=self.lesson, title="Broken").exists()
        )

    def test_educator_api_rejects_nan_coordinate(self):
        response = self.api.post(
            "/api/educator/annotations/",
            {
                "lesson": self.lesson.id,
                "title": "NaN spot",
                "description": "",
                "x": "nan",
                "y": 0,
                "z": 0,
                "order": 1,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("x", response.data)

    def test_public_lesson_api_survives_legacy_infinite_coordinate(self):
        Annotation.objects.create(
            lesson=self.lesson,
            title="Legacy bad",
            description="",
            position_x=float("inf"),
            position_y=0,
            position_z=0,
            order=1,
        )
        response = self.client.get(f"/api/lessons/{self.lesson.id}/")
        self.assertEqual(response.status_code, 200)
        coords = response.json()["annotations"][0]
        self.assertEqual(coords["x"], 0.0)
        self.assertTrue(all(isinstance(coords[k], float) for k in ("x", "y", "z")))
