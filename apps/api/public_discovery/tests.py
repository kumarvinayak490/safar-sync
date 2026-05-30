from __future__ import annotations

from datetime import date

import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import resolve
from rest_framework.test import APIClient

from organizer_media.models import OrganizerMediaItem
from organizer_policies.models import OrganizerPolicies
from organizer_profile.models import OrganizerProfile
from organizers.models import Organizer
from public_discovery.models import DemandPage
from trips.models import Trip, TripItineraryDay, TripPackage, TripPaymentSchedule

pytestmark = pytest.mark.django_db


def test_public_discovery_entry_routes_resolve_to_public_discovery_views():
    expected_routes = {
        "/api/public/discovery/": "public-discovery-catalog",
        "/api/public/organizers/": "public-organizer-page-list",
        "/api/public/organizers/kaza-field-collective/": "public-organizer-page-detail",
        (
            "/api/public/organizers/kaza-field-collective/trips/"
            "spiti-winter-field-week/"
        ): "public-organizer-trip-page-detail",
        "/api/public/trips/": "public-demand-page-index",
        "/api/public/trips/darjeeling-from-bihar/": "public-demand-page-shell",
    }

    for path, url_name in expected_routes.items():
        match = resolve(path)

        assert match.url_name == url_name
        assert match.func.view_class.__module__ == "public_discovery.views"


def test_public_discovery_catalog_lists_published_organizers_and_public_trip_pages():
    organizer = create_published_organizer("Kaza Field Collective")
    published_trip = create_published_trip(organizer, title="Spiti Winter Field Week")
    draft_organizer = Organizer.objects.create(name="Draft Mountain Notes")
    OrganizerProfile.objects.create(
        organizer=draft_organizer,
        public_description="Not visible yet.",
        publication_state=OrganizerProfile.PublicationState.DRAFT,
    )
    create_published_trip(draft_organizer, title="Hidden Organizer Trip")
    draft_trip = create_published_trip(organizer, title="Draft Trip")
    draft_trip.publication_state = Trip.PublicationState.DRAFT
    draft_trip.save(update_fields=["publication_state", "updated_at"])

    response = APIClient().get("/api/public/discovery/")

    payload = response.json()
    assert response.status_code == 200
    assert payload["surface"] == "public_discovery_catalog"
    assert payload["route_owner"] == "public_discovery"
    assert payload["entry_points"]["demand_page_api_template"] == (
        "/api/public/trips/{demand_slug}/"
    )
    assert [item["slug"] for item in payload["organizers"]] == [organizer.slug]
    assert [item["title"] for item in payload["trips"]] == [published_trip.title]


def test_public_organizer_page_composes_source_domain_content(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    organizer = create_published_organizer(
        "Kaza Field Collective",
        public_description="Field-tested trips through Spiti.",
    )
    create_public_organizer_media(organizer)
    create_published_trip(organizer, title="Spiti Winter Field Week")
    unpublished_trip = create_published_trip(organizer, title="Internal Route Notes")
    unpublished_trip.publication_state = Trip.PublicationState.DRAFT
    unpublished_trip.save(update_fields=["publication_state", "updated_at"])

    response = APIClient().get(f"/api/public/organizers/{organizer.slug}/")

    payload = response.json()
    assert response.status_code == 200
    assert payload["surface"] == "organizer_public_page"
    assert payload["route_owner"] == "public_discovery"
    assert payload["public_url_path"] == f"/organizers/{organizer.slug}/"
    assert payload["organizer_profile"]["identity"]["name"] == "Kaza Field Collective"
    assert payload["organizer_profile"]["public_description"] == (
        "Field-tested trips through Spiti."
    )
    assert payload["organizer_policies"]["privacy_policy"] == "Privacy terms."
    assert payload["media_items"][0]["caption"] == "Camp kitchen briefing"
    assert [trip["title"] for trip in payload["trips"]] == ["Spiti Winter Field Week"]


def test_public_trip_page_route_composes_trips_owned_public_page_content():
    organizer = create_published_organizer("Kaza Field Collective")
    trip = create_published_trip(organizer, title="Spiti Winter Field Week")

    response = APIClient().get(
        f"/api/public/organizers/{organizer.slug}/trips/{trip.slug}/"
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["surface"] == "public_trip_page"
    assert payload["route_owner"] == "public_discovery"
    assert payload["public_url_path"] == f"/organizers/{organizer.slug}/trips/{trip.slug}/"
    assert payload["legacy_public_url_path"] == f"/trips/{organizer.slug}/{trip.slug}"
    assert payload["trip"]["title"] == "Spiti Winter Field Week"
    assert payload["trip"]["organizer_identity"]["name"] == "Kaza Field Collective"
    assert [package["name"] for package in payload["trip"]["packages"]] == [
        "Shared room"
    ]


def test_existing_public_trip_route_remains_backward_compatible():
    organizer = create_published_organizer("Kaza Field Collective")
    trip = create_published_trip(organizer, title="Spiti Winter Field Week")

    response = APIClient().get(f"/api/public/trips/{organizer.slug}/{trip.slug}/")

    payload = response.json()
    assert response.status_code == 200
    assert payload["title"] == "Spiti Winter Field Week"
    assert payload["organizer_identity"]["name"] == "Kaza Field Collective"


def test_public_discovery_does_not_own_booking_or_checkout_routes():
    import public_discovery.urls

    forbidden_route_fragments = (
        "booking-readiness",
        "draft-bookings",
        "manual-payments",
        "payment-attempts",
        "checkout",
        "provider-confirmation",
    )
    discovery_patterns = [str(pattern.pattern) for pattern in public_discovery.urls.urlpatterns]

    for pattern in discovery_patterns:
        assert not any(fragment in pattern for fragment in forbidden_route_fragments)

    for path in (
        "/api/public/trips/kaza-field-collective/spiti-winter-field-week/draft-bookings/",
        "/api/public/trips/kaza-field-collective/spiti-winter-field-week/manual-payments/",
        "/api/public/bookings/42/payment-attempts/",
        "/api/public/payment-attempts/42/checkout-success/",
    ):
        match = resolve(path)

        assert not match.func.view_class.__module__.startswith("public_discovery")


def test_public_demand_page_index_lists_configured_publishable_pages():
    create_published_organizer("Kaza Field Collective")
    DemandPage.objects.create(
        title="Pattern Page",
        slug="pattern-page",
        demand_pattern="spiti",
        publication_state=DemandPage.PublicationState.PUBLISHED,
    )
    DemandPage.objects.create(
        title="Draft Page",
        slug="draft-page",
        demand_pattern="spiti",
        publication_state=DemandPage.PublicationState.DRAFT,
    )

    response = APIClient().get("/api/public/trips/")

    payload = response.json()
    assert response.status_code == 200
    assert payload["surface"] == "demand_page_index"
    assert [page["slug"] for page in payload["configured_demand_pages"]] == [
        "pattern-page",
    ]


def test_public_demand_page_shell_returns_configured_payload_with_selection():
    organizer = create_published_organizer("Kaza Field Collective")
    trip = create_published_trip(organizer, title="Spiti Winter Field Week")
    demand_page = DemandPage.objects.create(
        title="Spiti Demand",
        slug="spiti-demand",
        demand_pattern="",
        seo_title="Spiti Demand SEO",
        seo_copy="Spiti Demand landing copy",
        publication_state=DemandPage.PublicationState.DRAFT,
    )
    demand_page.selected_organizers.add(organizer)
    demand_page.selected_trips.add(trip)
    demand_page.publication_state = DemandPage.PublicationState.PUBLISHED
    demand_page.save()

    response = APIClient().get(f"/api/public/trips/{demand_page.slug}/")

    payload = response.json()
    assert response.status_code == 200
    assert payload["surface"] == "demand_page"
    assert payload["public_url_path"] == f"/trips/{demand_page.slug}/"
    assert payload["title"] == "Spiti Demand"
    assert payload["seo_title"] == "Spiti Demand SEO"
    assert payload["seo_copy"] == "Spiti Demand landing copy"
    assert payload["selection"]["selected_organizers"][0]["slug"] == organizer.slug
    assert payload["selection"]["selected_trips"][0]["slug"] == trip.slug


def test_public_demand_page_shell_returns_rule_matched_organizers_and_trips():
    organizer_match = create_published_organizer(
        "North Darjeeling Retreats",
        public_description="Mountain routes in the Darjeeling corridor.",
    )
    organizer_ignore = create_published_organizer(
        "Kashmir Valley Routes",
        public_description="Rocky ridges and river camps.",
    )
    darjeeling_trip = create_published_trip(
        organizer_match,
        title="Darjeeling Ridge Trek",
    )
    create_published_trip(organizer_match, title="Himalayan Winter Camp")
    create_published_trip(organizer_ignore, title="Kashmir Escape")

    demand_page = DemandPage.objects.create(
        title="Darjeeling From Bihar",
        slug="darjeeling-from-bihar",
        demand_pattern="darjeeling",
        publication_state=DemandPage.PublicationState.PUBLISHED,
    )

    response = APIClient().get(f"/api/public/trips/{demand_page.slug}/")
    payload = response.json()

    assert response.status_code == 200
    assert [organizer["slug"] for organizer in payload["selection"]["selected_organizers"]] == [
        organizer_match.slug
    ]
    assert [trip["slug"] for trip in payload["selection"]["selected_trips"]] == [
        darjeeling_trip.slug
    ]


def test_public_demand_page_shell_filters_unpublished_matches_from_rules():
    organizer_draft = Organizer.objects.create(name="Draft Darjeeling Group")
    OrganizerProfile.objects.create(
        organizer=organizer_draft,
        public_description="Darjeeling base camp logistics.",
        publication_state=OrganizerProfile.PublicationState.DRAFT,
    )
    published_organizer = create_published_organizer("Darjeeling Base Camp")
    create_published_trip(
        published_organizer,
        title="Clear Darjeeling Route",
    )
    draft_trip = create_published_trip(published_organizer, title="Draft Darjeeling Route")
    draft_trip.publication_state = Trip.PublicationState.DRAFT
    draft_trip.save(update_fields=["publication_state", "updated_at"])

    demand_page = DemandPage.objects.create(
        title="Darjeeling Draft Filter",
        slug="darjeeling-draft-filter",
        demand_pattern="darjeeling",
        publication_state=DemandPage.PublicationState.PUBLISHED,
    )

    response = APIClient().get(f"/api/public/trips/{demand_page.slug}/")
    payload = response.json()

    assert response.status_code == 200
    assert [organizer["slug"] for organizer in payload["selection"]["selected_organizers"]] == [
        published_organizer.slug
    ]
    assert [trip["slug"] for trip in payload["selection"]["selected_trips"]] == [
        "clear-darjeeling-route"
    ]


def test_public_demand_page_shell_returns_empty_selection_for_unmatched_pattern():
    demand_page = DemandPage.objects.create(
        title="No Match Pattern",
        slug="no-match-pattern",
        demand_pattern="antarctica",
        publication_state=DemandPage.PublicationState.PUBLISHED,
    )

    response = APIClient().get(f"/api/public/trips/{demand_page.slug}/")
    payload = response.json()

    assert response.status_code == 200
    assert payload["selection"]["selected_organizers"] == []
    assert payload["selection"]["selected_trips"] == []


def test_public_demand_page_payload_exposes_configured_seo_fields():
    demand_page = DemandPage.objects.create(
        title="SEO Demand",
        slug="seo-demand",
        seo_title="SEO Lead Demand Title",
        seo_copy="SEO specific landing copy for search visibility.",
        demand_pattern="darjeeling",
        publication_state=DemandPage.PublicationState.PUBLISHED,
    )

    response = APIClient().get(f"/api/public/trips/{demand_page.slug}/")
    payload = response.json()

    assert response.status_code == 200
    assert payload["slug"] == "seo-demand"
    assert payload["seo_title"] == "SEO Lead Demand Title"
    assert payload["seo_copy"] == "SEO specific landing copy for search visibility."


def test_public_demand_page_slug_collision_is_normalized_and_enforced():
    DemandPage.objects.create(
        title="First SEO Demand",
        slug="darjeeling-from-bihar",
        demand_pattern="darjeeling",
        publication_state=DemandPage.PublicationState.PUBLISHED,
    )

    with pytest.raises(ValidationError, match="already exists"):
        DemandPage.objects.create(
            title="Second SEO Demand",
            slug="Darjeeling-From-Bihar",
            demand_pattern="darjeeling",
            publication_state=DemandPage.PublicationState.PUBLISHED,
        )


def test_public_demand_page_shell_rejects_unconfigured_slug_or_unpublished_pages():
    response = APIClient().get("/api/public/trips/spurious-demand/")

    assert response.status_code == 404
    assert response.json()["detail"] == "Demand Page is not configured."

    DemandPage.objects.create(
        title="Unpublished Demand",
        slug="unpublished-demand",
        demand_pattern="draft",
        publication_state=DemandPage.PublicationState.DRAFT,
    )

    draft_response = APIClient().get("/api/public/trips/unpublished-demand/")
    assert draft_response.status_code == 404
    assert draft_response.json()["detail"] == "Demand Page is not configured."


def test_demand_page_validation_rejects_invalid_slug_and_unpublishable_state():
    with pytest.raises(ValidationError) as exc_info:
        DemandPage(title="Invalid Demand", slug="Not a slug!").full_clean()
    assert "slug" in exc_info.value.message_dict
    assert "valid “slug”" in str(exc_info.value.message_dict["slug"][0])

    with pytest.raises(ValidationError, match="Demand Page slug"):
        DemandPage(title="Invalid Demand", slug="bad_slug").full_clean()

    organizer = create_published_organizer("Spiti Hub")
    demand_page = DemandPage.objects.create(
        title="Publish Blocked",
        slug="publish-blocked",
        publication_state=DemandPage.PublicationState.DRAFT,
    )
    demand_page.publication_state = DemandPage.PublicationState.PUBLISHED

    with pytest.raises(ValidationError, match="Published Demand Pages must include"):
        demand_page.full_clean()

    demand_page.selected_organizers.add(organizer)
    demand_page.publication_state = DemandPage.PublicationState.PUBLISHED
    demand_page.full_clean()


def create_published_organizer(
    name: str,
    *,
    public_description: str = "Trustworthy field logistics.",
) -> Organizer:
    organizer = Organizer.objects.create(name=name)
    OrganizerPolicies.objects.create(
        organizer=organizer,
        privacy_policy="Privacy terms.",
        refund_policy="Refund terms.",
        cancellation_policy="Cancellation terms.",
    )
    OrganizerProfile.objects.create(
        organizer=organizer,
        public_description=public_description,
        publication_state=OrganizerProfile.PublicationState.PUBLISHED,
    )
    return organizer


def create_public_organizer_media(organizer: Organizer) -> OrganizerMediaItem:
    return OrganizerMediaItem.objects.create(
        organizer=organizer,
        image=SimpleUploadedFile("camp.png", b"image-bytes", content_type="image/png"),
        original_filename="camp.png",
        content_type="image/png",
        file_size=11,
        position=1,
        caption="Camp kitchen briefing",
        visibility=OrganizerMediaItem.Visibility.PUBLIC,
    )


def create_published_trip(organizer: Organizer, *, title: str) -> Trip:
    trip = Trip.objects.create(
        organizer=organizer,
        title=title,
        start_date=date(2026, 12, 10),
        end_date=date(2026, 12, 16),
        capacity=16,
        description_rich_text=rich_text_payload(f"{title} public details."),
        publication_state=Trip.PublicationState.PUBLISHED,
    )
    TripPackage.objects.create(
        trip=trip,
        name="Shared room",
        price_inr=42000,
        reservation_amount_inr=10000,
        position=1,
    )
    TripPaymentSchedule.objects.create(
        trip=trip,
        balance_due_days_before_start=21,
        balance_reminder_lead_days=5,
    )
    TripItineraryDay.objects.create(
        trip=trip,
        sequence=1,
        title="Arrival and readiness review",
        date_label="Day 1",
        description_rich_text=rich_text_payload("Settle in and review the route."),
    )
    return trip


def rich_text_payload(text: str) -> dict:
    return {
        "type": "doc",
        "content": [
            {
                "type": "paragraph",
                "content": [{"type": "text", "text": text}],
            }
        ],
    }
