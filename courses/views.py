from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_POST

from .models import Course, Lesson, StudentProgress

DEMO_COURSE_TITLE = "Demo: Explore a Box"


def home(request):
    demo_lesson = (
        Lesson.objects.filter(course__title=DEMO_COURSE_TITLE, order=1)
        .select_related("course")
        .first()
    )
    featured_courses = (
        Course.objects.exclude(title=DEMO_COURSE_TITLE)
        .annotate(lesson_count=Count("lessons"))
        .order_by("-updated_at")[:4]
    )
    return render(
        request,
        "courses/home.html",
        {
            "demo_lesson": demo_lesson,
            "featured_courses": featured_courses,
        },
    )


def course_list(request):
    courses = (
        Course.objects.exclude(title=DEMO_COURSE_TITLE)
        .annotate(lesson_count=Count("lessons"))
    )
    return render(request, "courses/course_list.html", {"courses": courses})


def course_detail(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    lessons = course.lessons.all()

    completed_ids = set()
    if request.user.is_authenticated:
        completed_ids = set(
            StudentProgress.objects.filter(
                student=request.user,
                lesson__course=course,
                completed=True,
            ).values_list("lesson_id", flat=True)
        )

    return render(
        request,
        "courses/course_detail.html",
        {
            "course": course,
            "lessons": lessons,
            "completed_ids": completed_ids,
            "progress": course.progress_for(request.user),
        },
    )


@ensure_csrf_cookie
def lesson_viewer(request, lesson_id):
    """Page shell for the 3D viewer. Model/hotspots load from the DRF API."""
    lesson = get_object_or_404(
        Lesson.objects.select_related("course"),
        id=lesson_id,
    )

    progress = None
    if request.user.is_authenticated:
        progress, _ = StudentProgress.objects.get_or_create(
            student=request.user,
            lesson=lesson,
        )

    viewer_config = {
        "lessonId": lesson.id,
        "lessonApiUrl": reverse("api-lesson-detail", args=[lesson.id]),
        "completeApiUrl": reverse("api-lesson-complete", args=[lesson.id]),
        "isAuthenticated": request.user.is_authenticated,
    }

    return render(
        request,
        "courses/lesson_viewer.html",
        {
            "lesson": lesson,
            "course": lesson.course,
            "progress": progress,
            "viewer_config": viewer_config,
        },
    )


@login_required
@require_POST
def mark_complete(request, lesson_id):
    """Kept for non-JS fallback; viewer prefers the DRF complete endpoint."""
    lesson = get_object_or_404(Lesson, id=lesson_id)
    progress, _ = StudentProgress.objects.get_or_create(
        student=request.user,
        lesson=lesson,
    )

    action = request.POST.get("action")
    if action == "complete":
        progress.completed = True
        progress.completed_at = timezone.now()
        progress.save()
        messages.success(request, f'Lesson "{lesson.title}" marked as complete.')
    elif action == "uncomplete":
        progress.completed = False
        progress.completed_at = None
        progress.save()
        messages.info(request, f'Lesson "{lesson.title}" marked as incomplete.')

    return redirect("lesson_viewer", lesson_id=lesson.id)
