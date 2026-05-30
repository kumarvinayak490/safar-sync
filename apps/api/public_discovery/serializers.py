from __future__ import annotations

from rest_framework import serializers

from organizer_media.selectors import public_organizer_media_payload
from organizer_policies.readiness import organizer_policies_for
from organizer_profile.identity import organizer_profile_identity_payload
from organizer_profile.publication import (
    organizer_profile_public_description,
    organizer_profile_publication_state,
)
from organizers.models import Organizer
from public_discovery.models import DemandPage
from public_discovery.selectors import (
    discovered_organizers_for_demand_page,
    discovered_trips_for_demand_page,
    published_public_trip_pages_for_organizer,
)
from trips.models import Trip
from trips.serializers import PublicTripSerializer


class DemandPageAdminSerializer(serializers.ModelSerializer):
    selected_organizer_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Organizer.objects.all(),
        source="selected_organizers",
        required=False,
    )
    selected_trip_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Trip.objects.all(),
        source="selected_trips",
        required=False,
    )

    class Meta:
        model = DemandPage
        fields = [
            "id",
            "slug",
            "title",
            "seo_title",
            "seo_copy",
            "demand_pattern",
            "publication_state",
            "selected_organizer_ids",
            "selected_trip_ids",
        ]

    def validate_slug(self, value: str) -> str:
        return value.strip().lower()

    def validate_title(self, value: str) -> str:
        return value.strip()

    def validate_seo_title(self, value: str) -> str:
        return (value or "").strip()

    def validate_seo_copy(self, value: str) -> str:
        return (value or "").strip()


def catalog_entry_points_payload() -> dict[str, str]:
    return {
        "catalog_api_path": "/api/public/discovery/",
        "organizer_pages_api_path": "/api/public/organizers/",
        "organizer_public_page_api_template": "/api/public/organizers/{organizer_slug}/",
        "public_trip_page_api_template": (
            "/api/public/organizers/{organizer_slug}/trips/{trip_slug}/"
        ),
        "demand_pages_api_path": "/api/public/trips/",
        "demand_page_api_template": "/api/public/trips/{demand_slug}/",
    }


def organizer_public_page_path(organizer: Organizer) -> str:
    return f"/organizers/{organizer.slug}/"


def public_trip_page_path(trip: Trip) -> str:
    return f"/organizers/{trip.organizer.slug}/trips/{trip.slug}/"


def demand_page_path(demand_slug: str) -> str:
    return f"/trips/{demand_slug}/"


def demand_page_index_payload(configured_demand_pages=()):
    return {
        "surface": "demand_page_index",
        "route_owner": "public_discovery",
        "public_url_path": "/trips/",
        "configured_demand_pages": [
            demand_page_summary_payload(page) for page in configured_demand_pages
        ],
    }


def demand_page_summary_payload(page) -> dict:
    return {
        "id": page.id,
        "slug": page.slug,
        "title": page.title,
        "public_url_path": demand_page_path(page.slug),
        "publication_state": page.publication_state,
    }


def demand_page_payload(page) -> dict:
    return {
        "surface": "demand_page",
        "route_owner": "public_discovery",
        "public_url_path": demand_page_path(page.slug),
        "slug": page.slug,
        "title": page.title,
        "seo_title": page.seo_title,
        "seo_copy": page.seo_copy,
        "demand_pattern": page.demand_pattern,
        "publication_state": page.publication_state,
        "selection": {
            "selected_organizers": [
                {
                    "id": organizer.id,
                    "slug": organizer.slug,
                    "name": organizer.name,
                    "public_url_path": organizer_public_page_path(organizer),
                }
                for organizer in discovered_organizers_for_demand_page(page)
            ],
            "selected_trips": [
                {
                    "id": trip.id,
                    "title": trip.title,
                    "slug": trip.slug,
                    "organizer": {
                        "id": trip.organizer_id,
                        "slug": trip.organizer.slug,
                        "public_url_path": organizer_public_page_path(trip.organizer),
                    },
                    "public_url_path": public_trip_page_path(trip),
                    "legacy_public_url_path": trip.public_url_path,
                }
                for trip in discovered_trips_for_demand_page(page)
            ],
        },
    }


def public_discovery_catalog_payload(
    *,
    organizers,
    trips,
    request=None,
) -> dict:
    return {
        "surface": "public_discovery_catalog",
        "route_owner": "public_discovery",
        "entry_points": catalog_entry_points_payload(),
        "organizers": [
            organizer_listing_payload(organizer, request=request)
            for organizer in organizers
        ],
        "trips": [public_trip_listing_payload(trip) for trip in trips],
    }


def organizer_listing_payload(organizer: Organizer, *, request=None) -> dict:
    return {
        "id": organizer.id,
        "slug": organizer.slug,
        "public_url_path": organizer_public_page_path(organizer),
        "organizer_profile": organizer_profile_summary_payload(
            organizer,
            request=request,
        ),
    }


def organizer_public_page_payload(
    organizer: Organizer,
    *,
    request=None,
    trips=None,
) -> dict:
    published_trips = (
        trips
        if trips is not None
        else published_public_trip_pages_for_organizer(organizer)
    )
    return {
        "surface": "organizer_public_page",
        "route_owner": "public_discovery",
        "public_url_path": organizer_public_page_path(organizer),
        "organizer_profile": organizer_profile_summary_payload(
            organizer,
            request=request,
        ),
        "media_items": public_organizer_media_payload(organizer, request=request),
        "organizer_policies": organizer_public_policies_payload(organizer),
        "trips": [public_trip_listing_payload(trip) for trip in published_trips],
    }


def organizer_profile_summary_payload(organizer: Organizer, *, request=None) -> dict:
    return {
        "id": organizer.id,
        "slug": organizer.slug,
        "identity": organizer_profile_identity_payload(organizer, request=request),
        "public_description": organizer_profile_public_description(organizer),
        "publication_state": organizer_profile_publication_state(organizer),
    }


def organizer_public_policies_payload(organizer: Organizer) -> dict[str, str]:
    policies = organizer_policies_for(organizer)
    return {
        "privacy_policy": policies.privacy_policy if policies is not None else "",
        "refund_policy": policies.refund_policy if policies is not None else "",
        "cancellation_policy": (
            policies.cancellation_policy if policies is not None else ""
        ),
    }


def public_trip_listing_payload(trip: Trip) -> dict:
    return {
        "id": trip.id,
        "title": trip.title,
        "slug": trip.slug,
        "start_date": trip.start_date,
        "end_date": trip.end_date,
        "publication_state": trip.publication_state,
        "organizer": {
            "id": trip.organizer_id,
            "slug": trip.organizer.slug,
            "public_url_path": organizer_public_page_path(trip.organizer),
        },
        "public_url_path": public_trip_page_path(trip),
        "legacy_public_url_path": trip.public_url_path,
    }


def public_trip_page_payload(trip: Trip, *, request=None) -> dict:
    return {
        "surface": "public_trip_page",
        "route_owner": "public_discovery",
        "public_url_path": public_trip_page_path(trip),
        "legacy_public_url_path": trip.public_url_path,
        "organizer_public_url_path": organizer_public_page_path(trip.organizer),
        "trip": PublicTripSerializer(trip, context={"request": request}).data,
    }


def demand_page_not_configured_payload(demand_slug: str) -> dict:
    return {
        "surface": "demand_page",
        "route_owner": "public_discovery",
        "public_url_path": demand_page_path(demand_slug),
        "detail": "Demand Page is not configured.",
    }
