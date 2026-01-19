from django.contrib import admin
from .models import Course, Lesson, StudentProgress, Annotation

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ['title', 'created_at']
    search_fields = ['tiitle', 'description']

@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ['title', 'course', 'order']
    list_filter = ['course']
    search_fields = ['title']

@admin.register(StudentProgress)
class StudentProgressAdmin(admin.ModelAdmin):
    list_display = ['student', 'lesson', 'completed', 'completed_at']
    list_filter = ['completed', 'student']

@admin.register(Annotation)
class AnnotationAdmin(admin.ModelAdmin):
    list_display = ['title', 'lesson', 'order']