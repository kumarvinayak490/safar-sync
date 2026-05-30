from django.apps import AppConfig


class TripPaymentsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "trip_payments"

    def ready(self):
        import trip_payments.signals  # noqa: F401
