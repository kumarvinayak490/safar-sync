from django.urls import path

from public_discovery.views import (
    PublicDemandPageIndexView,
    PublicDemandPageShellView,
    PublicDiscoveryCatalogView,
    PublicOrganizerPageDetailView,
    PublicOrganizerPageListView,
    PublicOrganizerTripPageDetailView,
)

urlpatterns = [
    path("discovery/", PublicDiscoveryCatalogView.as_view(), name="public-discovery-catalog"),
    path("organizers/", PublicOrganizerPageListView.as_view(), name="public-organizer-page-list"),
    path(
        "organizers/<slug:organizer_slug>/",
        PublicOrganizerPageDetailView.as_view(),
        name="public-organizer-page-detail",
    ),
    path(
        "organizers/<slug:organizer_slug>/trips/<slug:trip_slug>/",
        PublicOrganizerTripPageDetailView.as_view(),
        name="public-organizer-trip-page-detail",
    ),
    path("trips/", PublicDemandPageIndexView.as_view(), name="public-demand-page-index"),
    path(
        "trips/<slug:demand_slug>/",
        PublicDemandPageShellView.as_view(),
        name="public-demand-page-shell",
    ),
]
