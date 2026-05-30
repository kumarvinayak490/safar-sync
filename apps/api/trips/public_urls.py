from django.urls import path

from organizers.views import (
    PublicDraftBookingCreateView,
    PublicTripBookingReadinessView,
    PublicTripDetailView,
)
from trip_payments.views import PublicQrManualPaymentSubmissionView

urlpatterns = [
    path(
        "<int:trip_id>/booking-readiness/",
        PublicTripBookingReadinessView.as_view(),
        name="public-trip-booking-readiness",
    ),
    path(
        "<slug:organizer_slug>/<slug:trip_slug>/",
        PublicTripDetailView.as_view(),
        name="public-trip-detail",
    ),
    path(
        "<slug:organizer_slug>/<slug:trip_slug>/draft-bookings/",
        PublicDraftBookingCreateView.as_view(),
        name="public-draft-booking-create",
    ),
    path(
        "<slug:organizer_slug>/<slug:trip_slug>/manual-payments/",
        PublicQrManualPaymentSubmissionView.as_view(),
        name="public-qr-manual-payment-submission",
    ),
]
