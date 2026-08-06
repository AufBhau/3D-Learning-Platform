from django.conf import settings
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver


class Profile(models.Model):
    class Role(models.TextChoices):
        STUDENT = "student", "Student"
        EDUCATOR = "educator", "Educator"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.STUDENT,
    )

    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()})"

    @property
    def is_educator(self):
        return self.role == self.Role.EDUCATOR


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def ensure_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.get_or_create(user=instance)


def get_or_create_profile(user):
    profile, _ = Profile.objects.get_or_create(user=user)
    return profile


def user_is_educator(user):
    if not user.is_authenticated:
        return False
    return get_or_create_profile(user).is_educator
