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
    lessons = list(
        course.lessons.prefetch_related("annotations").all()
    )

    completed_ids = set()
    started_ids = set()
    if request.user.is_authenticated:
        progress_rows = StudentProgress.objects.filter(
            student=request.user,
            lesson__course=course,
        ).values_list("lesson_id", "completed")
        for lesson_id, completed in progress_rows:
            started_ids.add(lesson_id)
            if completed:
                completed_ids.add(lesson_id)

    flow_nodes = []
    found_current = False
    for index, lesson in enumerate(lessons):
        hotspot_titles = [a.title for a in lesson.annotations.all()[:4]]
        if lesson.id in completed_ids:
            status = "done"
        elif not found_current:
            status = "current"
            found_current = True
        else:
            status = "available"

        flow_nodes.append(
            {
                "lesson": lesson,
                "index": index + 1,
                "status": status,
                "hotspot_titles": hotspot_titles,
                "viewer_url": reverse("lesson_viewer", args=[lesson.id]),
            }
        )

    active_node = next(
        (n for n in flow_nodes if n["status"] == "current"),
        flow_nodes[0] if flow_nodes else None,
    )

    total = len(lessons)
    completed = len(completed_ids)
    progress = {
        "total": total,
        "completed": completed,
        "percent": int(round((completed / total) * 100)) if total else 0,
    }

    return render(
        request,
        "courses/course_detail.html",
        {
            "course": course,
            "lessons": lessons,
            "flow_nodes": flow_nodes,
            "active_node": active_node,
            "completed_ids": completed_ids,
            "progress": progress,
        },
    )


@ensure_csrf_cookie
def lesson_viewer(request, lesson_id):
    """Page shell for the 3D viewer. Model/hotspots load from the DRF API."""
    from accounts.models import user_is_educator

    lesson = get_object_or_404(
        Lesson.objects.select_related("course"),
        id=lesson_id,
    )

    progress = None
    if request.user.is_authenticated:
        # Read-only on GET; rows are created when marking complete/incomplete.
        progress = StudentProgress.objects.filter(
            student=request.user,
            lesson=lesson,
        ).first()

    # Educators previewing from dashboard should return to edit flows, not student pages.
    educator_return = None
    if (
        request.GET.get("from") == "educator"
        and request.user.is_authenticated
        and user_is_educator(request.user)
        and lesson.course.owner_id == request.user.id
    ):
        educator_return = {
            "lesson_edit_url": reverse("educator_lesson_edit", args=[lesson.id]),
            "course_detail_url": reverse(
                "educator_course_detail", args=[lesson.course_id]
            ),
        }

    next_lesson = (
        Lesson.objects.filter(course=lesson.course, order__gt=lesson.order)
        .order_by("order")
        .first()
    )
    next_lesson_url = None
    if next_lesson:
        next_lesson_url = reverse("lesson_viewer", args=[next_lesson.id])
        if educator_return:
            next_lesson_url = f"{next_lesson_url}?from=educator"

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
            "educator_return": educator_return,
            "next_lesson": next_lesson,
            "next_lesson_url": next_lesson_url,
        },
    )


@login_required
@require_POST
def mark_complete(request, lesson_id):
    """Kept for non-JS fallback; viewer prefers the DRF complete endpoint."""
    lesson = get_object_or_404(Lesson, id=lesson_id)
    progress, _ = StudentProgress.get_or_create_for(request.user, lesson)

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
    else:
        messages.error(request, "Unknown progress action.")

    return redirect("lesson_viewer", lesson_id=lesson.id)
