from django.db.models import Count
from rest_framework import viewsets
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser

from .models import Annotation, Course, Lesson
from .permissions import IsCourseOwner, IsEducator
from .serializers import (
    EducatorAnnotationSerializer,
    EducatorCourseSerializer,
    EducatorLessonSerializer,
)


class EducatorCourseViewSet(viewsets.ModelViewSet):
    serializer_class = EducatorCourseSerializer
    permission_classes = [IsEducator, IsCourseOwner]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_queryset(self):
        return Course.objects.filter(owner=self.request.user).annotate(
            lesson_count=Count("lessons")
        )

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class EducatorLessonViewSet(viewsets.ModelViewSet):
    serializer_class = EducatorLessonSerializer
    permission_classes = [IsEducator, IsCourseOwner]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_queryset(self):
        qs = Lesson.objects.filter(course__owner=self.request.user).annotate(
            hotspot_count=Count("annotations")
        )
        course_id = self.request.query_params.get("course")
        if course_id:
            qs = qs.filter(course_id=course_id)
        return qs

    def perform_create(self, serializer):
        serializer.save()


class EducatorAnnotationViewSet(viewsets.ModelViewSet):
    serializer_class = EducatorAnnotationSerializer
    permission_classes = [IsEducator, IsCourseOwner]

    def get_queryset(self):
        qs = Annotation.objects.filter(lesson__course__owner=self.request.user)
        lesson_id = self.request.query_params.get("lesson")
        if lesson_id:
            qs = qs.filter(lesson_id=lesson_id)
        return qs

    def perform_create(self, serializer):
        serializer.save()
