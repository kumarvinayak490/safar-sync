from __future__ import annotations

import re

from django.db.models import Prefetch, Q

from organizer_media.models import OrganizerMediaItem
from organizer_profile.models import OrganizerProfile
from organizers.models import Organizer
from public_discovery.models import DemandPage
from trips.models import Trip


def published_organizer_pages_queryset():
    return (
        Organizer.objects.select_related("organizer_profile", "organizer_policies")
        .prefetch_related(
            Prefetch(
                "organizer_media_items",
                queryset=OrganizerMediaItem.objects.public().ordered_for_display(),
            )
        )
        .filter(
            organizer_profile__publication_state=OrganizerProfile.PublicationState.PUBLISHED,
        )
        .order_by("name", "id")
    )


def published_public_trip_pages_queryset():
    return (
        Trip.objects.select_related("organizer", "payment_schedule")
        .prefetch_related("packages", "itinerary_days", "media_items__asset")
        .filter(
            publication_state=Trip.PublicationState.PUBLISHED,
            organizer__organizer_profile__publication_state=(
                OrganizerProfile.PublicationState.PUBLISHED
            ),
        )
        .order_by("start_date", "title", "id")
    )


def published_public_trip_pages_for_organizer(organizer: Organizer):
    return published_public_trip_pages_queryset().filter(organizer=organizer)


def published_discovery_pages_for_index():
    return (
        DemandPage.objects.filter(publication_state=DemandPage.PublicationState.PUBLISHED)
        .prefetch_related(
            Prefetch("selected_organizers"),
            Prefetch("selected_trips"),
        )
        .order_by("slug", "id")
    )


def published_discovery_page_for_slug(demand_slug: str):
    demand_page = (
        DemandPage.objects.filter(
            slug=demand_slug,
            publication_state=DemandPage.PublicationState.PUBLISHED,
        )
        .prefetch_related(
            Prefetch("selected_organizers"),
            Prefetch("selected_trips"),
        )
        .first()
    )
    if demand_page is None or not demand_page.is_discoverable:
        return None
    return demand_page


def discovered_organizers_for_demand_page(demand_page: DemandPage):
    selected_organizer_ids = list(
        demand_page.selected_organizers.filter(
            organizer_profile__publication_state=OrganizerProfile.PublicationState.PUBLISHED,
        ).values_list("id", flat=True)
    )
    pattern_query = _pattern_organizer_query(demand_page.demand_pattern)

    if not selected_organizer_ids and pattern_query is None:
        return Organizer.objects.none()

    if pattern_query is None:
        return Organizer.objects.filter(id__in=selected_organizer_ids).order_by(
            "name",
            "id",
        )

    return Organizer.objects.filter(
        Q(id__in=selected_organizer_ids)
        | pattern_query,
        organizer_profile__publication_state=OrganizerProfile.PublicationState.PUBLISHED,
    ).distinct().order_by("name", "id")


def discovered_trips_for_demand_page(demand_page: DemandPage):
    selected_trip_ids = list(
        demand_page.selected_trips.filter(
            publication_state=Trip.PublicationState.PUBLISHED,
            organizer__organizer_profile__publication_state=(
                OrganizerProfile.PublicationState.PUBLISHED
            ),
        ).values_list("id", flat=True)
    )
    pattern_query = _pattern_trip_query(demand_page.demand_pattern)

    if not selected_trip_ids and pattern_query is None:
        return Trip.objects.none()

    if pattern_query is None:
        return Trip.objects.filter(pk__in=selected_trip_ids).order_by(
            "start_date",
            "title",
            "id",
        )

    return Trip.objects.filter(
        Q(
            pk__in=selected_trip_ids,
        )
        | pattern_query,
        publication_state=Trip.PublicationState.PUBLISHED,
        organizer__organizer_profile__publication_state=(
            OrganizerProfile.PublicationState.PUBLISHED
        ),
    ).order_by(
        "start_date",
        "title",
        "id",
    )


def _pattern_terms(demand_pattern: str) -> list[str]:
    normalized = (demand_pattern or "").strip().lower()
    if not normalized:
        return []

    stop_words = {"from", "to", "the", "and", "of", "in", "on", "near", "for"}
    tokens = []
    for segment in re.split(r"[,;|]", normalized):
        for token in segment.split():
            cleaned = token.strip()
            if cleaned and cleaned not in stop_words:
                tokens.append(cleaned)

    return tokens


def _pattern_organizer_query(demand_pattern: str):
    terms = _pattern_terms(demand_pattern)
    if not terms:
        return None

    query = Q()
    for term in terms:
        query &= (
            Q(name__icontains=term)
            | Q(organizer_profile__public_description__icontains=term)
        )
    return query


def _pattern_trip_query(demand_pattern: str):
    terms = _pattern_terms(demand_pattern)
    if not terms:
        return None

    query = Q()
    for term in terms:
        query &= (
            Q(title__icontains=term)
            | Q(slug__icontains=term)
            | Q(description_rich_text__icontains=term)
            | Q(itinerary_days__title__icontains=term)
            | Q(itinerary_days__description_rich_text__icontains=term)
        )
    return query
