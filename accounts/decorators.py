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
                "Educator access required. Ask an administrator to grant educator access.",
            )
            return redirect("home")
        return view_func(request, *args, **kwargs)

    return _wrapped
