from __future__ import annotations

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from public_discovery.selectors import (
    published_discovery_page_for_slug,
    published_discovery_pages_for_index,
    published_organizer_pages_queryset,
    published_public_trip_pages_for_organizer,
    published_public_trip_pages_queryset,
)
from public_discovery.serializers import (
    demand_page_index_payload,
    demand_page_not_configured_payload,
    demand_page_payload,
    organizer_listing_payload,
    organizer_public_page_payload,
    public_discovery_catalog_payload,
    public_trip_page_payload,
)


class PublicDiscoveryCatalogView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        return Response(
            public_discovery_catalog_payload(
                organizers=published_organizer_pages_queryset(),
                trips=published_public_trip_pages_queryset(),
                request=request,
            )
        )


class PublicOrganizerPageListView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        return Response(
            {
                "surface": "organizer_public_page_index",
                "route_owner": "public_discovery",
                "organizers": [
                    organizer_listing_payload(organizer, request=request)
                    for organizer in published_organizer_pages_queryset()
                ],
            }
        )


class PublicOrganizerPageDetailView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, organizer_slug: str):
        organizer = get_object_or_404(
            published_organizer_pages_queryset(),
            slug=organizer_slug,
        )
        return Response(
            organizer_public_page_payload(
                organizer,
                request=request,
                trips=published_public_trip_pages_for_organizer(organizer),
            )
        )


class PublicOrganizerTripPageDetailView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, organizer_slug: str, trip_slug: str):
        trip = get_object_or_404(
            published_public_trip_pages_queryset(),
            organizer__slug=organizer_slug,
            slug=trip_slug,
        )
        return Response(public_trip_page_payload(trip, request=request))


class PublicDemandPageIndexView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        demand_pages = [
            page for page in published_discovery_pages_for_index() if page.is_discoverable
        ]
        return Response(demand_page_index_payload(configured_demand_pages=demand_pages))


class PublicDemandPageShellView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, demand_slug: str):
        demand_page = published_discovery_page_for_slug(demand_slug)
        if demand_page is not None:
            return Response(demand_page_payload(demand_page))

        return Response(
            demand_page_not_configured_payload(demand_slug),
            status=status.HTTP_404_NOT_FOUND,
        )
