from rest_framework.permissions import BasePermission

from accounts.models import user_is_educator


class IsEducator(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and user_is_educator(request.user)
        )


class IsCourseOwner(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        owner = getattr(obj, "owner", None)
        if owner is None and hasattr(obj, "course"):
            owner = getattr(obj.course, "owner", None)
        if owner is None and hasattr(obj, "lesson"):
            course = getattr(obj.lesson, "course", None)
            owner = getattr(course, "owner", None)
        return owner == request.user
