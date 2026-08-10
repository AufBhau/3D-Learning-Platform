from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .forms import SignUpForm
from .models import get_or_create_profile, user_is_educator


def _default_redirect(user):
    if user_is_educator(user):
        return "educator_dashboard"
    return "home"


def signup_view(request):
    if request.user.is_authenticated:
        return redirect(_default_redirect(request.user))

    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(
                request,
                f"Welcome {user.username}! Your account has been created.",
            )
            return redirect(_default_redirect(user))
    else:
        form = SignUpForm()

    return render(request, "accounts/signup.html", {"form": form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect(_default_redirect(request.user))

    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get("username")
            password = form.cleaned_data.get("password")
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f"Welcome back, {username}!")
                next_url = request.POST.get("next") or request.GET.get("next")
                if next_url and url_has_allowed_host_and_scheme(
                    next_url,
                    allowed_hosts={request.get_host()},
                    require_https=request.is_secure(),
                ):
                    return redirect(next_url)
                return redirect(_default_redirect(user))
    else:
        form = AuthenticationForm()

    return render(request, "accounts/login.html", {"form": form})


@require_POST
def logout_view(request):
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect("home")


@login_required
def profile_view(request):
    from courses.models import Annotation, Course, Lesson, StudentProgress
    from courses.views import DEMO_COURSE_TITLE

    profile = get_or_create_profile(request.user)

    courses = list(Course.objects.exclude(title=DEMO_COURSE_TITLE))
    course_cards = []
    for course in courses:
        progress = course.progress_for(request.user)
        course_cards.append(
            {
                "course": course,
                "lesson_count": progress["total"],
                "percent": progress["percent"],
                "completed": progress["completed"],
            }
        )

    completed_lessons = StudentProgress.objects.filter(
        student=request.user,
        completed=True,
    ).count()

    educator_stats = None
    if profile.is_educator:
        owned = Course.objects.filter(owner=request.user)
        educator_stats = {
            "courses": owned.count(),
            "lessons": Lesson.objects.filter(course__owner=request.user).count(),
            "hotspots": Annotation.objects.filter(
                lesson__course__owner=request.user
            ).count(),
        }

    return render(
        request,
        "accounts/profile.html",
        {
            "course_cards": course_cards,
            "total_courses": len(courses),
            "completed_lessons": completed_lessons,
            "profile": profile,
            "educator_stats": educator_stats,
        },
    )
