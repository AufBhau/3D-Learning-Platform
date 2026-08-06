from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect

from .models import user_is_educator


def educator_required(view_func):
    @login_required
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not user_is_educator(request.user):
            messages.error(
                request,
                "Educator access required. Sign up as an educator to use the dashboard.",
            )
            return redirect("home")
        return view_func(request, *args, **kwargs)

    return _wrapped
