from django.urls import path

from . import educator_views

urlpatterns = [
    path("", educator_views.dashboard, name="educator_dashboard"),
    path("courses/new/", educator_views.course_create, name="educator_course_create"),
    path(
        "courses/<int:course_id>/",
        educator_views.course_detail,
        name="educator_course_detail",
    ),
    path(
        "courses/<int:course_id>/edit/",
        educator_views.course_edit,
        name="educator_course_edit",
    ),
    path(
        "courses/<int:course_id>/delete/",
        educator_views.course_delete,
        name="educator_course_delete",
    ),
    path(
        "courses/<int:course_id>/lessons/new/",
        educator_views.lesson_create,
        name="educator_lesson_create",
    ),
    path(
        "lessons/<int:lesson_id>/edit/",
        educator_views.lesson_edit,
        name="educator_lesson_edit",
    ),
    path(
        "lessons/<int:lesson_id>/delete/",
        educator_views.lesson_delete,
        name="educator_lesson_delete",
    ),
    path(
        "lessons/<int:lesson_id>/hotspots/new/",
        educator_views.hotspot_create,
        name="educator_hotspot_create",
    ),
    path(
        "hotspots/<int:hotspot_id>/edit/",
        educator_views.hotspot_edit,
        name="educator_hotspot_edit",
    ),
    path(
        "hotspots/<int:hotspot_id>/delete/",
        educator_views.hotspot_delete,
        name="educator_hotspot_delete",
    ),
]
