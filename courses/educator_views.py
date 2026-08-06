from django.contrib import messages
from django.db.models import Count, Max
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.decorators import educator_required

from .educator_forms import AnnotationForm, CourseForm, LessonForm
from .models import Annotation, Course, Lesson


def _owned_course(user, course_id):
    return get_object_or_404(Course, id=course_id, owner=user)


def _owned_lesson(user, lesson_id):
    return get_object_or_404(Lesson, id=lesson_id, course__owner=user)


def _owned_hotspot(user, hotspot_id):
    return get_object_or_404(Annotation, id=hotspot_id, lesson__course__owner=user)


@educator_required
def dashboard(request):
    courses = (
        Course.objects.filter(owner=request.user)
        .annotate(
            lesson_count=Count("lessons", distinct=True),
            hotspot_count=Count("lessons__annotations", distinct=True),
        )
        .order_by("-updated_at")
    )

    owned_lessons = Lesson.objects.filter(course__owner=request.user)
    stats = {
        "courses": courses.count(),
        "lessons": owned_lessons.count(),
        "hotspots": Annotation.objects.filter(lesson__course__owner=request.user).count(),
        "with_models": owned_lessons.exclude(model_file="").count(),
    }

    # Per-course model count for cards
    for course in courses:
        course.modeled_lessons = course.lessons.exclude(model_file="").count()


    return render(
        request,
        "courses/educator/dashboard.html",
        {"courses": courses, "stats": stats},
    )


@educator_required
def course_create(request):
    if request.method == "POST":
        form = CourseForm(request.POST, request.FILES)
        if form.is_valid():
            course = form.save(commit=False)
            course.owner = request.user
            course.save()
            messages.success(request, f'Course "{course.title}" created.')
            return redirect("educator_course_detail", course_id=course.id)
    else:
        form = CourseForm()

    return render(
        request,
        "courses/educator/course_form.html",
        {"form": form, "page_title": "New course"},
    )


@educator_required
def course_edit(request, course_id):
    course = _owned_course(request.user, course_id)

    if request.method == "POST":
        form = CourseForm(request.POST, request.FILES, instance=course)
        if form.is_valid():
            form.save()
            messages.success(request, f'Course "{course.title}" updated.')
            return redirect("educator_course_detail", course_id=course.id)
    else:
        form = CourseForm(instance=course)

    return render(
        request,
        "courses/educator/course_form.html",
        {
            "form": form,
            "page_title": "Edit course",
            "course": course,
        },
    )


@educator_required
@require_POST
def course_delete(request, course_id):
    course = _owned_course(request.user, course_id)
    title = course.title
    course.delete()
    messages.info(request, f'Course "{title}" deleted.')
    return redirect("educator_dashboard")


@educator_required
def course_detail(request, course_id):
    course = _owned_course(request.user, course_id)
    lessons = course.lessons.annotate(hotspot_count=Count("annotations"))
    return render(
        request,
        "courses/educator/course_detail.html",
        {"course": course, "lessons": lessons},
    )


@educator_required
def lesson_create(request, course_id):
    course = _owned_course(request.user, course_id)
    next_order = (course.lessons.aggregate(m=Max("order")).get("m") or 0) + 1

    if request.method == "POST":
        form = LessonForm(request.POST, request.FILES)
        if form.is_valid():
            lesson = form.save(commit=False)
            lesson.course = course
            lesson.save()
            messages.success(
                request,
                f'Lesson "{lesson.title}" added. Upload a model if needed, then add hotspots below.',
            )
            return redirect("educator_lesson_edit", lesson_id=lesson.id)
    else:
        form = LessonForm(initial={"order": next_order})

    return render(
        request,
        "courses/educator/lesson_form.html",
        {
            "form": form,
            "course": course,
            "page_title": "New lesson",
        },
    )


@educator_required
def lesson_edit(request, lesson_id):
    lesson = _owned_lesson(request.user, lesson_id)

    if request.method == "POST":
        form = LessonForm(request.POST, request.FILES, instance=lesson)
        if form.is_valid():
            form.save()
            messages.success(request, f'Lesson "{lesson.title}" updated.')
            return redirect("educator_course_detail", course_id=lesson.course_id)
    else:
        form = LessonForm(instance=lesson)

    return render(
        request,
        "courses/educator/lesson_form.html",
        {
            "form": form,
            "course": lesson.course,
            "lesson": lesson,
            "page_title": "Edit lesson",
        },
    )


@educator_required
@require_POST
def lesson_delete(request, lesson_id):
    lesson = _owned_lesson(request.user, lesson_id)
    course_id = lesson.course_id
    title = lesson.title
    lesson.delete()
    messages.info(request, f'Lesson "{title}" deleted.')
    return redirect("educator_course_detail", course_id=course_id)


def _hotspot_placer_config(lesson, hotspot=None):
    annotations = [
        {
            "id": a.id,
            "title": a.title,
            "x": a.position_x,
            "y": a.position_y,
            "z": a.position_z,
        }
        for a in lesson.annotations.all()
    ]
    initial = None
    if hotspot is not None:
        initial = {
            "x": hotspot.position_x,
            "y": hotspot.position_y,
            "z": hotspot.position_z,
        }
    return {
        "modelUrl": lesson.model_url or "",
        "annotations": annotations,
        "editingId": hotspot.id if hotspot else None,
        "initialPosition": initial,
    }


@educator_required
def hotspot_create(request, lesson_id):
    lesson = _owned_lesson(request.user, lesson_id)
    next_order = (lesson.annotations.aggregate(m=Max("order")).get("m") or 0) + 1

    if request.method == "POST":
        form = AnnotationForm(request.POST)
        if form.is_valid():
            hotspot = form.save(commit=False)
            hotspot.lesson = lesson
            hotspot.save()
            messages.success(request, f'Hotspot "{hotspot.title}" added.')
            if request.POST.get("action") == "save_and_add_another":
                return redirect("educator_hotspot_create", lesson_id=lesson.id)
            return redirect("educator_lesson_edit", lesson_id=lesson.id)
    else:
        form = AnnotationForm(
            initial={
                "order": next_order,
                "position_x": 0,
                "position_y": 0,
                "position_z": 0,
            }
        )

    return render(
        request,
        "courses/educator/hotspot_form.html",
        {
            "form": form,
            "lesson": lesson,
            "course": lesson.course,
            "page_title": "Add hotspot",
            "placer_config": _hotspot_placer_config(lesson),
            "is_create": True,
        },
    )


@educator_required
def hotspot_edit(request, hotspot_id):
    hotspot = _owned_hotspot(request.user, hotspot_id)
    lesson = hotspot.lesson

    if request.method == "POST":
        form = AnnotationForm(request.POST, instance=hotspot)
        if form.is_valid():
            form.save()
            messages.success(request, f'Hotspot "{hotspot.title}" updated.')
            if request.POST.get("action") == "save_and_add_another":
                return redirect("educator_hotspot_create", lesson_id=lesson.id)
            return redirect("educator_lesson_edit", lesson_id=lesson.id)
    else:
        form = AnnotationForm(instance=hotspot)

    return render(
        request,
        "courses/educator/hotspot_form.html",
        {
            "form": form,
            "lesson": lesson,
            "course": lesson.course,
            "hotspot": hotspot,
            "page_title": "Edit hotspot",
            "placer_config": _hotspot_placer_config(lesson, hotspot),
            "is_create": False,
        },
    )


@educator_required
@require_POST
def hotspot_delete(request, hotspot_id):
    hotspot = _owned_hotspot(request.user, hotspot_id)
    lesson_id = hotspot.lesson_id
    title = hotspot.title
    hotspot.delete()
    messages.info(request, f'Hotspot "{title}" deleted.')
    return redirect("educator_lesson_edit", lesson_id=lesson_id)
