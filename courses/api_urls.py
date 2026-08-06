from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .api_views import (
    CourseDetailAPIView,
    CourseListAPIView,
    LessonDetailAPIView,
    MarkLessonCompleteAPIView,
    MyProgressAPIView,
)
from .educator_api import (
    EducatorAnnotationViewSet,
    EducatorCourseViewSet,
    EducatorLessonViewSet,
)

router = DefaultRouter()
router.register(r"educator/courses", EducatorCourseViewSet, basename="api-educator-course")
router.register(r"educator/lessons", EducatorLessonViewSet, basename="api-educator-lesson")
router.register(
    r"educator/annotations",
    EducatorAnnotationViewSet,
    basename="api-educator-annotation",
)

urlpatterns = [
    path("courses/", CourseListAPIView.as_view(), name="api-course-list"),
    path("courses/<int:pk>/", CourseDetailAPIView.as_view(), name="api-course-detail"),
    path("lessons/<int:pk>/", LessonDetailAPIView.as_view(), name="api-lesson-detail"),
    path(
        "lessons/<int:pk>/complete/",
        MarkLessonCompleteAPIView.as_view(),
        name="api-lesson-complete",
    ),
    path("me/progress/", MyProgressAPIView.as_view(), name="api-my-progress"),
    path("", include(router.urls)),
]
