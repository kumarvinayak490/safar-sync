from django.urls import path

from creative_setup.views import CreativeSetupView

urlpatterns = [
    path(
        "organizers/<int:organizer_id>/creative-setup/",
        CreativeSetupView.as_view(),
        name="organizer-creative-setup",
    ),
]
