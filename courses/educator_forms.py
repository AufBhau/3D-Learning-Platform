from django import forms

from .models import Annotation, Course, Lesson
from .validators import validate_course_thumbnail_size, validate_lesson_model_size


class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ["title", "description", "thumbnail"]
        widgets = {
            "title": forms.TextInput(attrs={"placeholder": "Course title"}),
            "description": forms.Textarea(attrs={"rows": 4}),
            "thumbnail": forms.ClearableFileInput(attrs={"accept": "image/*"}),
        }
        help_texts = {
            "thumbnail": "Shown on the course catalog and dashboard cards.",
        }

    def clean_thumbnail(self):
        return validate_course_thumbnail_size(self.cleaned_data.get("thumbnail"))


class LessonForm(forms.ModelForm):
    class Meta:
        model = Lesson
        fields = [
            "title",
            "description",
            "order",
            "model_file",
            "model_rotation_x",
            "model_rotation_y",
            "model_rotation_z",
            "camera_distance_factor",
            "camera_min_distance_factor",
            "camera_max_distance_factor",
            "interaction_guide",
        ]
        widgets = {
            "title": forms.TextInput(attrs={"placeholder": "Lesson title"}),
            "description": forms.Textarea(attrs={"rows": 3}),
            "interaction_guide": forms.Textarea(attrs={"rows": 3}),
            "model_rotation_x": forms.NumberInput(attrs={"step": "any"}),
            "model_rotation_y": forms.NumberInput(attrs={"step": "any"}),
            "model_rotation_z": forms.NumberInput(attrs={"step": "any"}),
            "camera_distance_factor": forms.NumberInput(attrs={"step": "any", "min": "0.05"}),
            "camera_min_distance_factor": forms.NumberInput(attrs={"step": "any", "min": "0.05"}),
            "camera_max_distance_factor": forms.NumberInput(attrs={"step": "any", "min": "0.1"}),
        }
        labels = {
            "model_rotation_x": "Model rotation X (°)",
            "model_rotation_y": "Model rotation Y (°)",
            "model_rotation_z": "Model rotation Z (°)",
            "camera_distance_factor": "Default zoom",
            "camera_min_distance_factor": "Zoom in limit (closest)",
            "camera_max_distance_factor": "Zoom out limit (farthest)",
        }
        help_texts = {
            "model_rotation_x": "Drag the preview to set this, then lock & save.",
            "model_rotation_y": "Updates live as you rotate the preview.",
            "model_rotation_z": "Any angle is allowed.",
            "camera_distance_factor": "Scroll the preview to zoom, then Lock zoom. 1 = auto-fit.",
            "camera_min_distance_factor": "How close students can zoom in (smaller = closer).",
            "camera_max_distance_factor": "How far students can zoom out (larger = farther).",
        }

    def clean(self):
        cleaned = super().clean()
        distance = cleaned.get("camera_distance_factor")
        zoom_min = cleaned.get("camera_min_distance_factor")
        zoom_max = cleaned.get("camera_max_distance_factor")
        if zoom_min is not None and zoom_max is not None and zoom_min > zoom_max:
            self.add_error(
                "camera_min_distance_factor",
                "Closest zoom must be less than or equal to farthest zoom.",
            )
        if (
            distance is not None
            and zoom_min is not None
            and zoom_max is not None
            and not (zoom_min <= distance <= zoom_max)
        ):
            self.add_error(
                "camera_distance_factor",
                "Default zoom must be between the closest and farthest limits.",
            )
        return cleaned

    def __init__(self, *args, course=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.course = course or getattr(self.instance, "course", None)

    def clean_order(self):
        order = self.cleaned_data["order"]
        if self.course is None:
            return order
        qs = Lesson.objects.filter(course=self.course, order=order)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError(
                "A lesson with this order already exists in this course."
            )
        return order

    def clean_model_file(self):
        return validate_lesson_model_size(self.cleaned_data.get("model_file"))


class AnnotationForm(forms.ModelForm):
    class Meta:
        model = Annotation
        fields = [
            "title",
            "description",
            "position_x",
            "position_y",
            "position_z",
            "order",
        ]
        widgets = {
            "title": forms.TextInput(attrs={"placeholder": "e.g. Motor shaft"}),
            "description": forms.Textarea(
                attrs={
                    "rows": 3,
                    "placeholder": "What should students learn here?",
                }
            ),
            "position_x": forms.NumberInput(
                attrs={"step": "any", "readonly": True, "id": "id_position_x"}
            ),
            "position_y": forms.NumberInput(
                attrs={"step": "any", "readonly": True, "id": "id_position_y"}
            ),
            "position_z": forms.NumberInput(
                attrs={"step": "any", "readonly": True, "id": "id_position_z"}
            ),
        }
        help_texts = {
            "position_x": "Filled when you click the model",
            "position_y": "Filled when you click the model",
            "position_z": "Filled when you click the model",
        }

    def __init__(self, *args, lesson=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.lesson = lesson or getattr(self.instance, "lesson", None)

    def clean_order(self):
        order = self.cleaned_data["order"]
        if self.lesson is None:
            return order
        qs = Annotation.objects.filter(lesson=self.lesson, order=order)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError(
                "A hotspot with this order already exists in this lesson."
            )
        return order
