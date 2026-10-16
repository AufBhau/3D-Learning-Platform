from django.contrib.auth.models import User
from django.core.validators import FileExtensionValidator
from django.db import IntegrityError, models, transaction


class Course(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    owner = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="owned_courses",
    )
    thumbnail = models.ImageField(
        upload_to="course_thumbnails/",
        blank=True,
        null=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

    def progress_for(self, user):
        """Return completed/total/percent for one user in this course."""
        total = self.lessons.count()
        if not user.is_authenticated or total == 0:
            return {"total": total, "completed": 0, "percent": 0}

        completed = self.lessons.filter(
            progress__student=user,
            progress__completed=True,
        ).count()
        return {
            "total": total,
            "completed": completed,
            "percent": int(round((completed / total) * 100)),
        }


class Lesson(models.Model):
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="lessons",
    )
    title = models.CharField(max_length=200)
    description = models.TextField()
    order = models.PositiveIntegerField(default=0)
    model_file = models.FileField(
        upload_to="3d_models/",
        blank=True,
        null=True,
        validators=[
            FileExtensionValidator(allowed_extensions=["glb", "gltf"]),
        ],
        help_text="Upload a .glb or .gltf 3D model",
    )
    interaction_guide = models.TextField(
        blank=True,
        help_text="Guide for students while exploring the model",
    )
    model_rotation_x = models.FloatField(
        default=0,
        help_text="Default model tilt around X, in degrees (e.g. 90).",
    )
    model_rotation_y = models.FloatField(
        default=0,
        help_text="Default model turn around Y, in degrees (e.g. 90).",
    )
    model_rotation_z = models.FloatField(
        default=0,
        help_text="Default model roll around Z, in degrees (e.g. 90).",
    )
    camera_distance_factor = models.FloatField(
        default=1.0,
        help_text="Default zoom vs auto-fit (1 = fitted, smaller = closer).",
    )
    camera_min_distance_factor = models.FloatField(
        default=0.25,
        help_text="Closest allowed zoom vs auto-fit (zoom in limit).",
    )
    camera_max_distance_factor = models.FloatField(
        default=6.0,
        help_text="Farthest allowed zoom vs auto-fit (zoom out limit).",
    )

    class Meta:
        ordering = ["course", "order"]
        unique_together = ["course", "order"]

    def __str__(self):
        return f"{self.course.title} - {self.title}"

    @property
    def model_url(self):
        if self.model_file:
            return self.model_file.url
        return ""

    @property
    def model_orientation(self):
        return {
            "x": self.model_rotation_x,
            "y": self.model_rotation_y,
            "z": self.model_rotation_z,
        }

    @property
    def camera_zoom(self):
        return {
            "distance": self.camera_distance_factor,
            "min": self.camera_min_distance_factor,
            "max": self.camera_max_distance_factor,
        }


class StudentProgress(models.Model):
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="lesson_progress",
    )
    lesson = models.ForeignKey(
        Lesson,
        on_delete=models.CASCADE,
        related_name="progress",
    )
    completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    time_spent = models.DurationField(null=True, blank=True)

    class Meta:
        unique_together = ["student", "lesson"]
        verbose_name_plural = "Student Progress"

    def __str__(self):
        return f"{self.student.username} - {self.lesson.title}"

    @classmethod
    def get_or_create_for(cls, student, lesson):
        """Race-safe get_or_create for the (student, lesson) unique pair."""
        try:
            with transaction.atomic():
                return cls.objects.get_or_create(student=student, lesson=lesson)
        except IntegrityError:
            return cls.objects.get(student=student, lesson=lesson), False


class Annotation(models.Model):
    lesson = models.ForeignKey(
        Lesson,
        on_delete=models.CASCADE,
        related_name="annotations",
    )
    title = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    position_x = models.FloatField(help_text="X position on the 3D model")
    position_y = models.FloatField(help_text="Y position on the 3D model")
    position_z = models.FloatField(help_text="Z position on the 3D model")
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["lesson", "order"]
        unique_together = ["lesson", "order"]

    def __str__(self):
        return f"{self.lesson.title} - {self.title}"

    def as_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "x": self.position_x,
            "y": self.position_y,
            "z": self.position_z,
            "order": self.order,
        }
