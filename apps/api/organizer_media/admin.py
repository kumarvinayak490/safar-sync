from django.contrib import admin

from organizer_media.models import OrganizerMediaItem


@admin.register(OrganizerMediaItem)
class OrganizerMediaItemAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "organizer",
        "original_filename",
        "visibility",
        "position",
        "created_at",
    )
    list_filter = ("visibility", "created_at")
    search_fields = ("organizer__name", "original_filename", "caption", "alt_text")
