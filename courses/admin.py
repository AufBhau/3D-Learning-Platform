from django.contrib import admin
from .models import Course, Lesson, StudentProgress, Annotation


class LessonInline(admin.TabularInline):
    model = Lesson
    extra = 1
    fields = ["title", "order", "model_file", "description"]
    show_change_link = True


class AnnotationInline(admin.TabularInline):
    model = Annotation
    extra = 1
    fields = [
        "title",
        "order",
        "position_x",
        "position_y",
        "position_z",
        "description",
    ]


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ["title", "owner", "created_at", "updated_at"]
    list_filter = ["owner"]
    search_fields = ["title", "description"]
    inlines = [LessonInline]


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ["title", "course", "order", "has_model"]
    list_filter = ["course"]
    search_fields = ["title", "description"]
    inlines = [AnnotationInline]

    @admin.display(boolean=True, description="3D model")
    def has_model(self, obj):
        return bool(obj.model_file)


@admin.register(StudentProgress)
class StudentProgressAdmin(admin.ModelAdmin):
    list_display = ["student", "lesson", "completed", "completed_at"]
    list_filter = ["completed", "student"]
    search_fields = ["student__username", "lesson__title"]


@admin.register(Annotation)
class AnnotationAdmin(admin.ModelAdmin):
    list_display = ["title", "lesson", "order"]
    list_filter = ["lesson__course"]
    search_fields = ["title", "lesson__title"]
