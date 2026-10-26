from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve

admin.site.site_header = "Administration Reaco"
admin.site.site_title = "Reaco"

urlpatterns = [
    path(settings.ADMIN_URL, admin.site.urls),
    path("compte/", include("apps.accounts.urls")),
    path("compte/", include("allauth.urls")),
    path("recettes/", include("apps.recipes.urls")),
    path("courses/", include("apps.shopping.urls")),
    path("api/", include("apps.api.urls")),
    path("", include("apps.pantry.urls")),
    path("", include("apps.core.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
elif settings.SERVE_MEDIA:
    urlpatterns += [
        re_path(r"^media/(?P<path>.*)$", serve, {"document_root": settings.MEDIA_ROOT}),
    ]
