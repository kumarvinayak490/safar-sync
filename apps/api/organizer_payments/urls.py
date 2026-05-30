from django.urls import path

from organizers.urls import ORGANIZER_PAYMENT_URLPATTERNS
from organizers.views import PublicBookingReadinessView

urlpatterns = [
    *ORGANIZER_PAYMENT_URLPATTERNS,
    path(
        "public/organizers/<int:organizer_id>/booking-readiness/",
        PublicBookingReadinessView.as_view(),
        name="public-booking-readiness",
    ),
]
