from accounts.models import get_or_create_profile


def role_context(request):
    is_educator = False
    if getattr(request, "user", None) is not None and request.user.is_authenticated:
        is_educator = get_or_create_profile(request.user).is_educator
    return {"is_educator": is_educator}
