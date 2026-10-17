"""Simple cache-backed rate limit helpers (login / sensitive POSTs)."""

from django.conf import settings
from django.core.cache import cache


def _client_key(request, prefix):
    user = getattr(request, "user", None)
    if user is not None and getattr(user, "is_authenticated", False):
        identity = f"user:{user.pk}"
    else:
        identity = f"ip:{request.META.get('REMOTE_ADDR', 'unknown')}"
    return f"{prefix}:{identity}"


def too_many_attempts(request, *, prefix="login", limit=None, window=None):
    limit = limit if limit is not None else getattr(settings, "LOGIN_ATTEMPT_LIMIT", 5)
    key = _client_key(request, prefix)
    return cache.get(key, 0) >= limit


def record_failed_attempt(request, *, prefix="login", window=None):
    window = window if window is not None else getattr(
        settings, "LOGIN_ATTEMPT_WINDOW", 300
    )
    key = _client_key(request, prefix)
    try:
        cache.incr(key)
    except ValueError:
        cache.set(key, 1, timeout=window)


def clear_attempts(request, *, prefix="login"):
    cache.delete(_client_key(request, prefix))
