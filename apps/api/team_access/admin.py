from django.contrib import admin

from team_access.models import OrganizerInvitation, OrganizerMembership


@admin.register(OrganizerMembership)
class OrganizerMembershipAdmin(admin.ModelAdmin):
    list_display = ["organizer", "user", "role", "created_at"]
    list_filter = ["role"]
    search_fields = ["organizer__name", "user__username", "user__email"]


@admin.register(OrganizerInvitation)
class OrganizerInvitationAdmin(admin.ModelAdmin):
    list_display = ["organizer", "email", "role", "status", "last_sent_at"]
    list_filter = ["role", "status"]
    search_fields = ["organizer__name", "email", "token"]
    readonly_fields = ["token", "last_sent_at", "accepted_at", "revoked_at"]
