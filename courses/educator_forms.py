from django import forms

from .models import Annotation, Course, Lesson


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


class LessonForm(forms.ModelForm):
    class Meta:
        model = Lesson
        fields = [
            "title",
            "description",
            "order",
            "model_file",
            "interaction_guide",
        ]
        widgets = {
            "title": forms.TextInput(attrs={"placeholder": "Lesson title"}),
            "description": forms.Textarea(attrs={"rows": 3}),
            "interaction_guide": forms.Textarea(attrs={"rows": 3}),
        }


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
