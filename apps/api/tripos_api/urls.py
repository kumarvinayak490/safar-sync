from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from health.views import ServiceIndexView

urlpatterns = [
    path("", ServiceIndexView.as_view(), name="service-index"),
    path("admin/", admin.site.urls),
    path("api/health/", include("health.urls")),
    path("api/internal-admin/", include("internal_admin.urls")),
    path("api/public/", include("public_discovery.urls")),
    path("api/public/trips/", include("trips.public_urls")),
    path("api/", include("organizer_profile.urls")),
    path("api/", include("organizer_media.urls")),
    path("api/", include("team_access.urls")),
    path("api/", include("organizer_payments.urls")),
    path("api/", include("trips.urls")),
    path("api/", include("trip_operations.urls")),
    path("api/", include("trip_payments.urls")),
    path("api/", include("trip_travelers.urls")),
    path("api/", include("creative_setup.urls")),
    path("api/", include("organizer_policies.urls")),
    path("api/", include("trip_bookings.urls")),
    path("api/", include("organizers.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
