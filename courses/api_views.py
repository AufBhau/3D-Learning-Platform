from django.shortcuts import get_object_or_404
from django.db.models import Count
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Course, Lesson, StudentProgress
from .serializers import (
    CourseDetailSerializer,
    CourseListSerializer,
    LessonDetailSerializer,
    MarkCompleteSerializer,
    ProgressSerializer,
)


class CourseListAPIView(generics.ListAPIView):
    serializer_class = CourseListSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        return Course.objects.annotate(lesson_count=Count("lessons"))


class CourseDetailAPIView(generics.RetrieveAPIView):
    serializer_class = CourseDetailSerializer
    permission_classes = [AllowAny]
    queryset = Course.objects.prefetch_related("lessons")


class LessonDetailAPIView(generics.RetrieveAPIView):
    serializer_class = LessonDetailSerializer
    permission_classes = [AllowAny]
    queryset = Lesson.objects.select_related("course").prefetch_related("annotations")


class MarkLessonCompleteAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        lesson = get_object_or_404(Lesson, pk=pk)
        serializer = MarkCompleteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        progress, _ = StudentProgress.objects.get_or_create(
            student=request.user,
            lesson=lesson,
        )
        action = serializer.validated_data["action"]

        if action == "complete":
            progress.completed = True
            progress.completed_at = timezone.now()
            progress.save()
            message = f'Lesson "{lesson.title}" marked as complete.'
        else:
            progress.completed = False
            progress.completed_at = None
            progress.save()
            message = f'Lesson "{lesson.title}" marked as incomplete.'

        return Response(
            {
                "message": message,
                "completed": progress.completed,
                "completed_at": progress.completed_at,
                "lesson_id": lesson.id,
            },
            status=status.HTTP_200_OK,
        )


class MyProgressAPIView(generics.ListAPIView):
    serializer_class = ProgressSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return StudentProgress.objects.filter(
            student=self.request.user
        ).select_related("lesson", "lesson__course")
