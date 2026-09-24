from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.views.static import serve

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("courses.api_urls")),
    path("api-auth/", include("rest_framework.urls")),
    path("accounts/", include("accounts.urls")),
    path("educator/", include("courses.educator_urls")),
    path("", include("courses.urls")),
]

static_root = (
    settings.STATICFILES_DIRS[0] if settings.DEBUG else settings.STATIC_ROOT
)
urlpatterns += [
    re_path(r"^media/(?P<path>.*)$", serve, {"document_root": settings.MEDIA_ROOT}),
    re_path(r"^static/(?P<path>.*)$", serve, {"document_root": static_root}),
]
