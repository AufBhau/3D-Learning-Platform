from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from accounts.models import Profile
from courses.educator_forms import LessonForm
from courses.models import Course, Lesson, StudentProgress


class LessonOrderValidationTests(TestCase):
    def setUp(self):
        self.educator = User.objects.create_user("teacher", password="pass12345")
        Profile.objects.filter(user=self.educator).update(role=Profile.Role.EDUCATOR)
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


class QueryBudgetTests(TestCase):
    def setUp(self):
        self.educator = User.objects.create_user("ed", password="pass12345")
        Profile.objects.filter(user=self.educator).update(role=Profile.Role.EDUCATOR)
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
