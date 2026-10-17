from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from .models import Annotation, Course, Lesson, StudentProgress
from .validators import (
    validate_course_thumbnail_size,
    validate_finite_float,
    validate_lesson_model_file,
    validate_positive_finite,
)


def _drf_validate(validate_fn, value, **kwargs):
    try:
        return validate_fn(value, **kwargs) if kwargs else validate_fn(value)
    except DjangoValidationError as exc:
        raise serializers.ValidationError(exc.messages) from exc


class AnnotationSerializer(serializers.ModelSerializer):
    x = serializers.FloatField(source="position_x")
    y = serializers.FloatField(source="position_y")
    z = serializers.FloatField(source="position_z")

    class Meta:
        model = Annotation
        fields = ["id", "title", "description", "x", "y", "z", "order"]


class LessonListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lesson
        fields = ["id", "title", "description", "order"]


class LessonDetailSerializer(serializers.ModelSerializer):
    model_url = serializers.SerializerMethodField()
    model_orientation = serializers.SerializerMethodField()
    camera_zoom = serializers.SerializerMethodField()
    annotations = AnnotationSerializer(many=True, read_only=True)
    course_id = serializers.IntegerField(source="course.id", read_only=True)
    course_title = serializers.CharField(source="course.title", read_only=True)
    completed = serializers.SerializerMethodField()

    class Meta:
        model = Lesson
        fields = [
            "id",
            "title",
            "description",
            "order",
            "interaction_guide",
            "model_url",
            "model_orientation",
            "camera_zoom",
            "annotations",
            "course_id",
            "course_title",
            "completed",
        ]

    def get_model_url(self, obj):
        return obj.model_url

    def get_model_orientation(self, obj):
        return obj.model_orientation

    def get_camera_zoom(self, obj):
        return obj.camera_zoom

    def get_completed(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False
        return StudentProgress.objects.filter(
            student=request.user,
            lesson=obj,
            completed=True,
        ).exists()


class CourseListSerializer(serializers.ModelSerializer):
    lesson_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Course
        fields = [
            "id",
            "title",
            "description",
            "thumbnail",
            "lesson_count",
            "created_at",
        ]


class CourseDetailSerializer(serializers.ModelSerializer):
    lessons = LessonListSerializer(many=True, read_only=True)
    progress = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = [
            "id",
            "title",
            "description",
            "thumbnail",
            "created_at",
            "updated_at",
            "lessons",
            "progress",
        ]

    def get_progress(self, obj):
        request = self.context.get("request")
        if not request:
            return {"total": obj.lessons.count(), "completed": 0, "percent": 0}
        return obj.progress_for(request.user)


class ProgressSerializer(serializers.ModelSerializer):
    lesson_id = serializers.IntegerField(source="lesson.id", read_only=True)
    lesson_title = serializers.CharField(source="lesson.title", read_only=True)
    course_id = serializers.IntegerField(source="lesson.course_id", read_only=True)
    course_title = serializers.CharField(source="lesson.course.title", read_only=True)

    class Meta:
        model = StudentProgress
        fields = [
            "id",
            "lesson_id",
            "lesson_title",
            "course_id",
            "course_title",
            "completed",
            "completed_at",
        ]


class MarkCompleteSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["complete", "uncomplete"])


class EducatorCourseSerializer(serializers.ModelSerializer):
    lesson_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Course
        fields = [
            "id",
            "title",
            "description",
            "thumbnail",
            "lesson_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "lesson_count", "created_at", "updated_at"]

    def validate_thumbnail(self, value):
        return _drf_validate(validate_course_thumbnail_size, value)


class EducatorLessonSerializer(serializers.ModelSerializer):
    model_url = serializers.SerializerMethodField(read_only=True)
    hotspot_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Lesson
        fields = [
            "id",
            "course",
            "title",
            "description",
            "order",
            "model_file",
            "model_url",
            "model_rotation_x",
            "model_rotation_y",
            "model_rotation_z",
            "camera_distance_factor",
            "camera_min_distance_factor",
            "camera_max_distance_factor",
            "interaction_guide",
            "hotspot_count",
        ]
        read_only_fields = ["id", "model_url", "hotspot_count"]
        # Prefer validate() field error over default UniqueTogetherValidator wording.
        validators = []

    def get_model_url(self, obj):
        return obj.model_url

    def validate_course(self, course):
        request = self.context.get("request")
        if request and course.owner_id != request.user.id:
            raise serializers.ValidationError("You can only add lessons to your own courses.")
        return course

    def validate_model_file(self, value):
        return _drf_validate(validate_lesson_model_file, value)

    def validate_camera_distance_factor(self, value):
        return _drf_validate(
            validate_positive_finite, value, label="Default zoom", minimum=0.05
        )

    def validate_camera_min_distance_factor(self, value):
        return _drf_validate(
            validate_positive_finite, value, label="Closest zoom", minimum=0.05
        )

    def validate_camera_max_distance_factor(self, value):
        return _drf_validate(
            validate_positive_finite, value, label="Farthest zoom", minimum=0.1
        )

    def validate_model_rotation_x(self, value):
        return _drf_validate(validate_finite_float, value, label="Rotation X")

    def validate_model_rotation_y(self, value):
        return _drf_validate(validate_finite_float, value, label="Rotation Y")

    def validate_model_rotation_z(self, value):
        return _drf_validate(validate_finite_float, value, label="Rotation Z")

    def validate(self, attrs):
        attrs = super().validate(attrs)
        course = attrs.get("course") or getattr(self.instance, "course", None)
        order = attrs.get("order", getattr(self.instance, "order", None))
        if course is not None and order is not None:
            qs = Lesson.objects.filter(course=course, order=order)
            if self.instance is not None:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError(
                    {
                        "order": "A lesson with this order already exists in this course.",
                    }
                )

        distance = attrs.get(
            "camera_distance_factor",
            getattr(self.instance, "camera_distance_factor", None),
        )
        zoom_min = attrs.get(
            "camera_min_distance_factor",
            getattr(self.instance, "camera_min_distance_factor", None),
        )
        zoom_max = attrs.get(
            "camera_max_distance_factor",
            getattr(self.instance, "camera_max_distance_factor", None),
        )
        errors = {}
        if zoom_min is not None and zoom_max is not None and zoom_min > zoom_max:
            errors["camera_min_distance_factor"] = (
                "Closest zoom must be less than or equal to farthest zoom."
            )
        if (
            distance is not None
            and zoom_min is not None
            and zoom_max is not None
            and not (zoom_min <= distance <= zoom_max)
        ):
            errors["camera_distance_factor"] = (
                "Default zoom must be between the closest and farthest limits."
            )
        if errors:
            raise serializers.ValidationError(errors)
        return attrs


class EducatorAnnotationSerializer(serializers.ModelSerializer):
    x = serializers.FloatField(source="position_x")
    y = serializers.FloatField(source="position_y")
    z = serializers.FloatField(source="position_z")

    class Meta:
        model = Annotation
        fields = [
            "id",
            "lesson",
            "title",
            "description",
            "x",
            "y",
            "z",
            "order",
        ]
        read_only_fields = ["id"]
        validators = []

    def validate_lesson(self, lesson):
        request = self.context.get("request")
        if request and lesson.course.owner_id != request.user.id:
            raise serializers.ValidationError("You can only add hotspots to your own lessons.")
        return lesson

    def validate(self, attrs):
        attrs = super().validate(attrs)
        lesson = attrs.get("lesson") or getattr(self.instance, "lesson", None)
        order = attrs.get("order", getattr(self.instance, "order", None))
        if lesson is None or order is None:
            return attrs
        qs = Annotation.objects.filter(lesson=lesson, order=order)
        if self.instance is not None:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                {
                    "order": "A hotspot with this order already exists in this lesson.",
                }
            )
        return attrs
