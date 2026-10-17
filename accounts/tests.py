from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.models import Profile, get_or_create_profile


class SignupTests(TestCase):
    def test_signup_always_creates_student(self):
        response = self.client.post(
            reverse("signup"),
            {
                "username": "newstudent",
                "password1": "complex-pass-12345",
                "password2": "complex-pass-12345",
                "role": "educator",  # ignored / not a form field
            },
        )
        self.assertEqual(response.status_code, 302)
        user = User.objects.get(username="newstudent")
        self.assertEqual(user.profile.role, Profile.Role.STUDENT)


class ProfileCacheTests(TestCase):
    def test_get_or_create_profile_reuses_cached_instance(self):
        user = User.objects.create_user("cached", password="x")
        first = get_or_create_profile(user)
        with self.assertNumQueries(0):
            second = get_or_create_profile(user)
        self.assertIs(first, second)


class EducatorGateMessageTests(TestCase):
    def test_student_sees_admin_grant_message(self):
        user = User.objects.create_user("plain", password="pass12345")
        self.client.force_login(user)
        response = self.client.get(reverse("educator_dashboard"), follow=True)
        self.assertContains(
            response,
            "Ask an administrator to grant educator access",
        )


class LoginThrottleTests(TestCase):
    def setUp(self):
        cache.clear()
        User.objects.create_user("victim", password="correct-horse-battery")

    @override_settings(LOGIN_ATTEMPT_LIMIT=3, LOGIN_ATTEMPT_WINDOW=60)
    def test_login_locks_after_repeated_failures(self):
        for _ in range(3):
            response = self.client.post(
                reverse("login"),
                {"username": "victim", "password": "wrong-password"},
            )
            self.assertIn(response.status_code, (200, 429))

        locked = self.client.post(
            reverse("login"),
            {"username": "victim", "password": "wrong-password"},
        )
        self.assertEqual(locked.status_code, 429)
        self.assertContains(
            locked, "Too many failed login attempts", status_code=429
        )

        # Even the correct password stays locked until the window expires.
        still_locked = self.client.post(
            reverse("login"),
            {"username": "victim", "password": "correct-horse-battery"},
        )
        self.assertEqual(still_locked.status_code, 429)

    @override_settings(LOGIN_ATTEMPT_LIMIT=5, LOGIN_ATTEMPT_WINDOW=60)
    def test_successful_login_clears_failures(self):
        self.client.post(
            reverse("login"),
            {"username": "victim", "password": "wrong-password"},
        )
        response = self.client.post(
            reverse("login"),
            {"username": "victim", "password": "correct-horse-battery"},
        )
        self.assertEqual(response.status_code, 302)
