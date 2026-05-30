from django.apps import AppConfig


class OrganizersConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "organizers"

    def ready(self):
        import organizers.signals  # noqa: F401
