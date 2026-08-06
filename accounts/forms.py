from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import Profile


class SignUpForm(UserCreationForm):
    role = forms.ChoiceField(
        choices=Profile.Role.choices,
        initial=Profile.Role.STUDENT,
        widget=forms.RadioSelect,
        help_text="Students learn. Educators create courses and upload 3D models.",
    )

    class Meta:
        model = User
        fields = ("username", "role", "password1", "password2")

    def save(self, commit=True):
        user = super().save(commit=commit)
        profile, _ = Profile.objects.get_or_create(user=user)
        profile.role = self.cleaned_data["role"]
        profile.save()
        return user


class RoleSwitchForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ["role"]
        widgets = {"role": forms.RadioSelect}
        help_texts = {
            "role": "Switch between learning as a student and creating content as an educator.",
        }
