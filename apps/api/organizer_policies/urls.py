from django.urls import path

from organizer_policies.views import OrganizerPoliciesView

urlpatterns = [
    path(
        "organizers/<int:organizer_id>/policies/",
        OrganizerPoliciesView.as_view(),
        name="organizer-policies",
    ),
]
