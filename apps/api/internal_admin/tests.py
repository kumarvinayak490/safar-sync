from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

import pytest
from django.apps import apps
from django.contrib.auth import get_user_model
from django.urls import resolve
from django.utils import timezone
from rest_framework.test import APIClient

from organizers.models import Organizer
from public_discovery.models import DemandPage
from trip_bookings.models import Booking
from trip_operations.models import ActivityLog
from trip_payments.models import (
    PaymentAttempt,
    PaymentException,
    PlatformFeeStatement,
    ProviderPayment,
)
from trip_payments.payment_exceptions import record_late_confirmed_payment_exception
from trip_travelers.models import TravelerSlot
from trips.models import Trip, TripPackage, TripPaymentSchedule


@dataclass(frozen=True)
class RequestUser:
    id: int
    email: str
    is_staff: bool
    is_authenticated: bool = True


def test_internal_admin_shell_is_staff_only():
    staff_user = RequestUser(
        id=1,
        email="staff@example.com",
        is_staff=True,
    )
    non_staff_user = RequestUser(
        id=2,
        email="operator@example.com",
        is_staff=False,
    )
    client = APIClient()

    client.force_authenticate(non_staff_user)
    non_staff_response = client.get("/api/internal-admin/")

    client.force_authenticate(staff_user)
    staff_response = client.get("/api/internal-admin/")

    assert non_staff_response.status_code == 403
    assert staff_response.status_code == 200
    assert staff_response.json()["surface"] == "internal_admin"
    assert staff_response.json()["business_state_owner"] == "source_domain_modules"
    assert staff_response.json()["staff"] == {
        "id": staff_user.id,
        "email": "staff@example.com",
        "is_staff": True,
    }
    surfaces = {
        surface["key"]: surface
        for surface in staff_response.json()["orchestration_surfaces"]
    }
    assert surfaces["platform_fee_statement_review"]["source_domain"] == "trip_payments"
    assert surfaces["payment_exception_review"]["source_domain"] == "trip_payments"
    assert surfaces["discovery_page_config"]["source_domain"] == "public_discovery"


def test_internal_admin_shell_has_no_business_models():
    assert list(apps.get_app_config("internal_admin").get_models()) == []


def test_existing_internal_admin_module_routes_still_resolve():
    match = resolve("/api/internal-admin/organizers/")

    assert match.url_name == "internal-admin-organizer-list"


@pytest.mark.django_db
def test_internal_admin_can_configure_demand_pages_and_read_back_ownership_surface():
    owner = Organizer.objects.create(name="Kaza Valley Collective")
    trip = Trip.objects.create(
        organizer=owner,
        title="Darjeeling Base Camp",
        start_date=date(2026, 11, 1),
        end_date=date(2026, 11, 6),
        capacity=16,
    )
    staff = create_user("internal-admin-discovery@example.com", is_staff=True)
    non_staff = create_user("internal-admin-operator@example.com")
    client = APIClient()

    client.force_authenticate(non_staff)
    non_staff_list_response = client.get("/api/internal-admin/discovery-pages/")
    non_staff_create_response = client.post(
        "/api/internal-admin/discovery-pages/",
        {
            "slug": "darjeeling-from-bihar",
            "title": "Darjeeling From Bihar",
            "demand_pattern": "darjeeling",
            "selected_organizer_ids": [owner.id],
            "selected_trip_ids": [trip.id],
        },
        format="json",
    )

    client.force_authenticate(staff)
    list_response = client.get("/api/internal-admin/discovery-pages/")
    create_response = client.post(
        "/api/internal-admin/discovery-pages/",
        {
            "slug": "darjeeling-from-bihar",
            "title": "Darjeeling From Bihar",
            "demand_pattern": "darjeeling",
            "selected_organizer_ids": [owner.id],
            "selected_trip_ids": [trip.id],
        },
        format="json",
    )

    demand_page = DemandPage.objects.get()
    detail_response = client.get(f"/api/internal-admin/discovery-pages/{demand_page.id}/")
    patch_response = client.patch(
        f"/api/internal-admin/discovery-pages/{demand_page.id}/",
        {"publication_state": DemandPage.PublicationState.PUBLISHED},
        format="json",
    )

    assert non_staff_list_response.status_code == 403
    assert non_staff_create_response.status_code == 403
    assert list_response.status_code == 200
    assert create_response.status_code == 201
    assert create_response.json()["slug"] == "darjeeling-from-bihar"
    assert detail_response.status_code == 200
    assert detail_response.json()["selected_organizer_ids"] == [owner.id]
    assert detail_response.json()["selected_trip_ids"] == [trip.id]
    assert demand_page.publication_state == DemandPage.PublicationState.DRAFT
    assert patch_response.status_code == 200
    demand_page.refresh_from_db()
    assert demand_page.publication_state == DemandPage.PublicationState.PUBLISHED
    assert demand_page.selected_trips.filter(pk=trip.id).exists()
    assert demand_page.selected_organizers.filter(pk=owner.id).exists()


@pytest.mark.django_db
def test_internal_admin_platform_fee_statement_review_is_staff_only_and_trip_payments_owned():
    booking = create_booking(title="Platform Fee Staff Review")
    create_provider_payment(
        booking,
        provider_attempt_reference="order_staff_statement_001",
        provider_payment_reference="pay_staff_statement_001",
        confirmed_at=timezone.make_aware(datetime(2026, 5, 20, 10, 0)),
    )
    staff = create_user("statement-staff@example.com", is_staff=True)
    non_staff = create_user("statement-owner@example.com")
    client = APIClient()

    client.force_authenticate(non_staff)
    non_staff_response = client.get("/api/internal-admin/platform-fee-statements/")

    client.force_authenticate(staff)
    create_response = client.post(
        "/api/internal-admin/platform-fee-statements/",
        {
            "organizer": booking.trip.organizer_id,
            "period_start": "2026-05-01",
            "status": PlatformFeeStatement.Status.ISSUED,
            "notes": "May pilot statement.",
        },
        format="json",
    )
    statement = PlatformFeeStatement.objects.get()
    patch_response = client.patch(
        f"/api/internal-admin/platform-fee-statements/{statement.id}/",
        {"status": PlatformFeeStatement.Status.COLLECTED, "refresh_totals": True},
        format="json",
    )

    assert non_staff_response.status_code == 403
    assert create_response.status_code == 201
    assert create_response.json()["platform_fee_amount_inr"] == 160
    assert create_response.json()["provider_payment_count"] == 1
    assert patch_response.status_code == 200
    assert patch_response.json()["status"] == PlatformFeeStatement.Status.COLLECTED
    assert PlatformFeeStatement.__module__ == "trip_payments.models"
    assert list(apps.get_app_config("internal_admin").get_models()) == []


@pytest.mark.django_db
def test_internal_admin_payment_exception_review_is_staff_only_and_resolves_source_record():
    booking = create_booking(title="Payment Exception Staff Review")
    provider_payment = create_provider_payment(
        booking,
        provider_attempt_reference="order_staff_exception_001",
        provider_payment_reference="pay_staff_exception_001",
    )
    payment_exception = record_late_confirmed_payment_exception(
        provider_payment,
        payment_attempt=provider_payment.payment_attempt,
    )
    staff = create_user("exception-staff@example.com", is_staff=True)
    non_staff = create_user("exception-owner@example.com")
    client = APIClient()

    client.force_authenticate(non_staff)
    non_staff_list_response = client.get("/api/internal-admin/payment-exceptions/")
    non_staff_resolve_response = client.post(
        f"/api/internal-admin/payment-exceptions/{payment_exception.id}/resolve/",
        {"resolution_note": "Should not be accepted."},
        format="json",
    )

    client.force_authenticate(staff)
    list_response = client.get(
        "/api/internal-admin/payment-exceptions/",
        {
            "organizer": booking.trip.organizer_id,
            "status": PaymentException.Status.OPEN,
        },
    )
    detail_response = client.get(
        f"/api/internal-admin/payment-exceptions/{payment_exception.id}/"
    )
    resolve_response = client.post(
        f"/api/internal-admin/payment-exceptions/{payment_exception.id}/resolve/",
        {"resolution_note": "Staff reviewed pilot handling."},
        format="json",
    )

    payment_exception.refresh_from_db()
    assert non_staff_list_response.status_code == 403
    assert non_staff_resolve_response.status_code == 403
    assert list_response.status_code == 200
    assert list_response.json()[0]["id"] == payment_exception.id
    assert list_response.json()[0]["organizer_name"] == booking.trip.organizer.name
    assert list_response.json()[0]["available_review_actions"] == [
        "resolve_booking_operations"
    ]
    assert detail_response.status_code == 200
    assert detail_response.json()["booking_contact_name"] == "Asha Nair"
    assert resolve_response.status_code == 200
    assert resolve_response.json()["status"] == (
        PaymentException.Status.BOOKING_OPERATIONS_RESOLVED
    )
    assert payment_exception.status == PaymentException.Status.BOOKING_OPERATIONS_RESOLVED
    assert payment_exception.resolved_by == staff
    assert payment_exception.resolution_note == "Staff reviewed pilot handling."
    assert PaymentException.__module__ == "trip_payments.models"
    assert ActivityLog.objects.filter(
        booking=booking,
        action=ActivityLog.Action.PAYMENT_EXCEPTION_RESOLVED,
        actor=staff,
        metadata__payment_exception_id=payment_exception.id,
    ).exists()


@pytest.mark.django_db
def test_internal_admin_payment_exception_review_uses_trip_payments_resolution_rules():
    booking = create_booking(title="Mismatched Exception Staff Review")
    payment_attempt = PaymentAttempt.objects.create(
        booking=booking,
        amount_inr=8000,
        provider_attempt_reference="order_staff_mismatch_001",
    )
    payment_exception = PaymentException.objects.create(
        organizer=booking.trip.organizer,
        trip=booking.trip,
        booking=booking,
        payment_attempt=payment_attempt,
        exception_type=PaymentException.ExceptionType.MISMATCHED_PROVIDER_PAYMENT,
        provider=PaymentAttempt.Provider.RAZORPAY,
        amount_inr=7999,
        provider_attempt_reference=payment_attempt.provider_attempt_reference,
        provider_payment_reference="pay_staff_mismatch_001",
        mismatch_reasons=["amount"],
        details={"reason": "amount_mismatch"},
    )
    staff = create_user("mismatch-staff@example.com", is_staff=True)
    client = APIClient()
    client.force_authenticate(staff)

    response = client.post(
        f"/api/internal-admin/payment-exceptions/{payment_exception.id}/resolve/",
        {"resolution_note": "Tried unsupported staff resolution."},
        format="json",
    )

    payment_exception.refresh_from_db()
    assert response.status_code == 400
    assert payment_exception.status == PaymentException.Status.OPEN


def create_user(email: str, *, is_staff: bool = False):
    user = get_user_model().objects.create_user(
        username=email,
        email=email,
        password="password",
    )
    if is_staff:
        user.is_staff = True
        user.save(update_fields=["is_staff"])
    return user


def create_booking(*, title: str) -> Booking:
    organizer = Organizer.objects.create(name=f"{title} Collective")
    trip = Trip.objects.create(
        organizer=organizer,
        title=title,
        start_date=date(2026, 7, 10),
        end_date=date(2026, 7, 15),
        capacity=8,
    )
    TripPaymentSchedule.objects.create(trip=trip, balance_due_days_before_start=3)
    package = TripPackage.objects.create(
        trip=trip,
        name="Base",
        price_inr=32000,
        reservation_amount_inr=8000,
        position=1,
    )
    booking = Booking.objects.create(
        trip=trip,
        booking_contact_name="Asha Nair",
        booking_contact_phone="+919876543210",
        booking_state=Booking.BookingState.RESERVED,
    )
    TravelerSlot.objects.create(booking=booking, package=package, position=1)
    return booking


def create_provider_payment(
    booking: Booking,
    *,
    provider_attempt_reference: str,
    provider_payment_reference: str,
    confirmed_at=None,
) -> ProviderPayment:
    payment_attempt = PaymentAttempt.objects.create(
        booking=booking,
        amount_inr=8000,
        status=PaymentAttempt.Status.CONFIRMED,
        provider_attempt_reference=provider_attempt_reference,
    )
    return ProviderPayment.objects.create(
        booking=booking,
        payment_attempt=payment_attempt,
        amount_inr=8000,
        provider_payment_reference=provider_payment_reference,
        confirmed_at=confirmed_at or timezone.now(),
    )
