from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("courses.api_urls")),
    path("api-auth/", include("rest_framework.urls")),
    path("accounts/", include("accounts.urls")),
    path("educator/", include("courses.educator_urls")),
    path("", include("courses.urls")),
]

if settings.DEBUG:
    urlpatterns += static(
        settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0]
    )

# Media stays on local disk for this app (PythonAnywhere-friendly).
# Static files in production are served by WhiteNoise from STATIC_ROOT.
if settings.DEBUG or getattr(settings, "SERVE_MEDIA", True):
    urlpatterns += [
        re_path(
            r"^media/(?P<path>.*)$",
            serve,
            {"document_root": settings.MEDIA_ROOT},
        ),
    ]
