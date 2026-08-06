from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("courses/", views.course_list, name="course_list"),
    path("courses/<int:course_id>/", views.course_detail, name="course_detail"),
    path("viewer/<int:lesson_id>/", views.lesson_viewer, name="lesson_viewer"),
    path(
        "lesson/<int:lesson_id>/complete/",
        views.mark_complete,
        name="mark_complete",
    ),
]
