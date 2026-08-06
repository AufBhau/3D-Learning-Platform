from rest_framework import serializers

from .models import Annotation, Course, Lesson, StudentProgress


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
            "annotations",
            "course_id",
            "course_title",
            "completed",
        ]

    def get_model_url(self, obj):
        return obj.model_url

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
            "interaction_guide",
            "hotspot_count",
        ]
        read_only_fields = ["id", "model_url", "hotspot_count"]

    def get_model_url(self, obj):
        return obj.model_url

    def validate_course(self, course):
        request = self.context.get("request")
        if request and course.owner_id != request.user.id:
            raise serializers.ValidationError("You can only add lessons to your own courses.")
        return course


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

    def validate_lesson(self, lesson):
        request = self.context.get("request")
        if request and lesson.course.owner_id != request.user.id:
            raise serializers.ValidationError("You can only add hotspots to your own lessons.")
        return lesson
