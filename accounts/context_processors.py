from accounts.models import get_or_create_profile, user_is_educator


def role_context(request):
    is_educator = False
    if getattr(request, "user", None) is not None and request.user.is_authenticated:
        is_educator = user_is_educator(request.user)
        get_or_create_profile(request.user)
    return {"is_educator": is_educator}
