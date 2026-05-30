from django.contrib import admin

from organizers.models import (
    ActivityLog,
    Booking,
    BookingAccessLink,
    BookingAdjustment,
    BookingImport,
    BookingImportRow,
    LedgerEntry,
    ManualPayment,
    ManualPaymentInstructions,
    Notification,
    OpeningPaymentRecord,
    Organizer,
    PaymentAttempt,
    PaymentException,
    PayoutAccount,
    PlatformFeeStatement,
    ProviderAuthorizationSession,
    ProviderConnectionTestResult,
    ProviderPayment,
    ProviderPaymentSetup,
    RefundRecord,
    SeatHold,
    SensitiveProviderCredential,
    SensitiveProviderCredentialAudit,
    TravelerDocument,
    TravelerSlot,
    Trip,
    TripPackage,
    TripPaymentSchedule,
)
from trip_payments.platform_fees import refresh_platform_fee_statement


@admin.register(Organizer)
class OrganizerAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "identity_name", "identity_whatsapp_number", "created_at"]
    search_fields = ["name", "slug", "identity_name", "identity_whatsapp_number"]


@admin.register(PayoutAccount)
class PayoutAccountAdmin(admin.ModelAdmin):
    list_display = [
        "organizer",
        "status",
        "settlement_readiness_source",
        "support_confirmed_by",
        "support_confirmed_at",
        "holder_name",
        "updated_at",
    ]
    list_filter = ["status", "settlement_readiness_source"]
    search_fields = ["organizer__name", "holder_name", "provider_account_reference"]


@admin.register(ProviderPaymentSetup)
class ProviderPaymentSetupAdmin(admin.ModelAdmin):
    list_display = [
        "organizer",
        "provider",
        "status",
        "authorization_state",
        "provider_verification_status",
        "provider_connection_state",
        "provider_mode",
        "provider_payment_capability_enabled",
        "updated_at",
    ]
    list_filter = [
        "provider",
        "status",
        "authorization_method",
        "authorization_state",
        "provider_verification_status",
        "provider_connection_state",
        "provider_mode",
        "provider_payment_capability_enabled",
    ]
    search_fields = ["organizer__name", "provider_merchant_reference"]


@admin.register(ManualPaymentInstructions)
class ManualPaymentInstructionsAdmin(admin.ModelAdmin):
    list_display = [
        "organizer",
        "original_filename",
        "upi_id",
        "account_name",
        "updated_at",
    ]
    search_fields = ["organizer__name", "upi_id", "account_name"]
    readonly_fields = [
        "original_filename",
        "content_type",
        "file_size",
        "created_at",
        "updated_at",
    ]


@admin.register(SensitiveProviderCredential)
class SensitiveProviderCredentialAdmin(admin.ModelAdmin):
    list_display = [
        "organizer",
        "provider",
        "provider_mode",
        "credential_kind",
        "status",
        "provider_account_reference",
        "encryption_key_id",
        "last_accessed_at",
        "updated_at",
    ]
    list_filter = ["provider", "provider_mode", "credential_kind", "status"]
    search_fields = ["organizer__name", "provider_account_reference"]
    readonly_fields = [
        "organizer",
        "provider_payment_setup",
        "provider",
        "provider_mode",
        "credential_kind",
        "status",
        "provider_account_reference",
        "scopes",
        "expires_at",
        "encryption_key_id",
        "credential_fingerprint",
        "last_accessed_at",
        "rotated_at",
        "revoked_at",
        "revoked_reason",
        "created_by",
        "rotated_by",
        "revoked_by",
        "created_at",
        "updated_at",
    ]
    exclude = ["encrypted_payload"]

    def has_add_permission(self, request):
        return False


@admin.register(SensitiveProviderCredentialAudit)
class SensitiveProviderCredentialAuditAdmin(admin.ModelAdmin):
    list_display = [
        "organizer",
        "credential",
        "event_type",
        "actor",
        "occurred_at",
    ]
    list_filter = ["event_type", "occurred_at"]
    search_fields = ["organizer__name", "credential__provider_account_reference"]
    readonly_fields = [
        "organizer",
        "credential",
        "event_type",
        "actor",
        "metadata",
        "occurred_at",
        "created_at",
    ]

    def has_add_permission(self, request):
        return False


@admin.register(ProviderAuthorizationSession)
class ProviderAuthorizationSessionAdmin(admin.ModelAdmin):
    list_display = [
        "organizer",
        "provider",
        "provider_mode",
        "status",
        "initiated_by",
        "provider_account_reference",
        "expires_at",
        "updated_at",
    ]
    list_filter = ["provider", "provider_mode", "status", "expires_at"]
    search_fields = ["organizer__name", "provider_account_reference", "initiated_by__email"]
    readonly_fields = [
        "organizer",
        "provider_payment_setup",
        "provider",
        "provider_mode",
        "status",
        "client_id",
        "redirect_uri",
        "scopes",
        "provider_account_reference",
        "failure_reason",
        "initiated_by",
        "expires_at",
        "completed_at",
        "failed_at",
        "created_at",
        "updated_at",
    ]
    exclude = ["state_digest"]

    def has_add_permission(self, request):
        return False


@admin.register(ProviderConnectionTestResult)
class ProviderConnectionTestResultAdmin(admin.ModelAdmin):
    list_display = [
        "organizer",
        "provider",
        "provider_mode",
        "status",
        "initiated_by",
        "initiated_by_staff",
        "started_at",
        "completed_at",
    ]
    list_filter = ["provider", "provider_mode", "status", "initiated_by_staff", "started_at"]
    search_fields = [
        "organizer__name",
        "provider_account_reference",
        "provider_order_reference",
        "provider_payment_reference",
        "initiated_by__email",
    ]
    readonly_fields = [
        "organizer",
        "provider_payment_setup",
        "provider",
        "provider_mode",
        "status",
        "provider_account_reference",
        "provider_order_reference",
        "provider_payment_reference",
        "checks",
        "checkout_payload",
        "failure_reason",
        "initiated_by",
        "initiated_by_staff",
        "started_at",
        "completed_at",
        "created_at",
        "updated_at",
    ]

    def has_add_permission(self, request):
        return False


class TripPackageInline(admin.TabularInline):
    model = TripPackage
    extra = 1


class TripPaymentScheduleInline(admin.StackedInline):
    model = TripPaymentSchedule
    extra = 0
    max_num = 1


class TravelerSlotInline(admin.TabularInline):
    model = TravelerSlot
    extra = 0
    readonly_fields = [
        "position",
        "package",
        "traveler_state",
        "booked_package_price_inr",
        "booked_reservation_amount_inr",
        "attendance_marked_at",
        "attendance_marked_by",
        "cancelled_at",
        "created_at",
    ]
    fields = [
        "position",
        "package",
        "traveler_state",
        "booked_package_price_inr",
        "booked_reservation_amount_inr",
        "traveler_full_name",
        "traveler_phone",
        "traveler_email",
        "cancellation_reason",
        "cancelled_at",
        "replaced_by_slot",
        "addition_reserved_at",
        "attendance_state",
        "attendance_marked_at",
        "attendance_marked_by",
        "emergency_contact_name",
        "emergency_contact_phone",
        "created_at",
    ]


class LedgerEntryInline(admin.TabularInline):
    model = LedgerEntry
    extra = 0
    readonly_fields = [
        "entry_type",
        "amount_inr",
        "currency",
        "provider_payment",
        "manual_payment",
        "opening_payment_record",
        "booking_adjustment",
        "refund_record",
        "occurred_at",
        "created_at",
    ]
    can_delete = False


@admin.register(Trip)
class TripAdmin(admin.ModelAdmin):
    list_display = [
        "title",
        "organizer",
        "start_date",
        "end_date",
        "capacity",
        "publication_state",
        "booking_availability",
    ]
    list_filter = ["publication_state", "booking_availability", "start_date"]
    search_fields = ["title", "organizer__name", "slug"]
    inlines = [TripPackageInline, TripPaymentScheduleInline]


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "trip",
        "booking_contact_name",
        "booking_state",
        "draft_expires_at",
        "created_at",
    ]
    list_filter = ["booking_state", "draft_expires_at"]
    search_fields = [
        "trip__title",
        "booking_contact_name",
        "booking_contact_phone",
        "booking_contact_email",
    ]
    inlines = [TravelerSlotInline, LedgerEntryInline]


@admin.register(PaymentAttempt)
class PaymentAttemptAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "booking",
        "provider",
        "purpose",
        "status",
        "amount_inr",
        "created_at",
    ]
    list_filter = ["provider", "purpose", "status", "created_at"]
    search_fields = [
        "booking__booking_contact_name",
        "booking__booking_contact_phone",
        "provider_attempt_reference",
    ]


@admin.register(SeatHold)
class SeatHoldAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "trip",
        "booking",
        "payment_attempt",
        "seat_count",
        "expires_at",
        "released_at",
    ]
    list_filter = ["expires_at", "released_at"]
    search_fields = [
        "booking__booking_contact_name",
        "booking__booking_contact_phone",
        "payment_attempt__provider_attempt_reference",
    ]


@admin.register(ProviderPayment)
class ProviderPaymentAdmin(admin.ModelAdmin):
    list_display = [
        "provider_payment_reference",
        "booking",
        "provider",
        "amount_inr",
        "provider_fee_amount_inr",
        "provider_net_settlement_amount_inr",
        "confirmed_at",
    ]
    list_filter = ["provider", "confirmed_at"]
    search_fields = [
        "booking__booking_contact_name",
        "booking__booking_contact_phone",
        "provider_payment_reference",
    ]


@admin.register(PlatformFeeStatement)
class PlatformFeeStatementAdmin(admin.ModelAdmin):
    list_display = [
        "organizer",
        "period_label",
        "status",
        "provider_payment_count",
        "gross_provider_payment_amount_inr",
        "platform_fee_amount_inr",
        "generated_at",
        "issued_at",
        "collected_at",
    ]
    list_filter = ["status", "period_start", "issued_at", "collected_at"]
    search_fields = ["organizer__name", "organizer__slug", "notes"]
    readonly_fields = [
        "period_label",
        "period_end",
        "currency",
        "provider_payment_count",
        "gross_provider_payment_amount_inr",
        "platform_fee_amount_inr",
        "generated_at",
        "created_at",
        "updated_at",
    ]
    actions = ["refresh_statement_totals"]

    @admin.action(description="Refresh Platform Fee Statement totals")
    def refresh_statement_totals(self, request, queryset):
        refreshed_count = 0
        for statement in queryset.select_related("organizer"):
            refresh_platform_fee_statement(statement)
            refreshed_count += 1
        self.message_user(
            request,
            f"Refreshed {refreshed_count} Platform Fee Statement total(s).",
        )

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        refresh_platform_fee_statement(obj)


@admin.register(PaymentException)
class PaymentExceptionAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "exception_type",
        "status",
        "booking",
        "provider",
        "amount_inr",
        "provider_payment_reference",
        "created_at",
    ]
    list_filter = ["exception_type", "status", "provider", "created_at", "resolved_at"]
    search_fields = [
        "booking__booking_contact_name",
        "booking__booking_contact_phone",
        "provider_attempt_reference",
        "provider_payment_reference",
        "provider_dispute_reference",
    ]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(ManualPayment)
class ManualPaymentAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "booking",
        "source",
        "status",
        "amount_inr",
        "payment_reference",
        "approved_at",
    ]
    list_filter = ["source", "status", "submitted_at", "approved_at"]
    search_fields = [
        "booking__booking_contact_name",
        "booking__booking_contact_phone",
        "payment_reference",
        "original_filename",
    ]
    readonly_fields = ["created_at", "updated_at"]


class BookingImportRowInline(admin.TabularInline):
    model = BookingImportRow
    extra = 0
    readonly_fields = [
        "row_number",
        "booking",
        "status",
        "conflict_code",
        "message",
        "payload",
        "created_at",
    ]
    can_delete = False


@admin.register(BookingImport)
class BookingImportAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "trip",
        "status",
        "created_count",
        "updated_count",
        "skipped_count",
        "conflict_count",
        "created_at",
    ]
    list_filter = ["status", "created_at"]
    search_fields = ["trip__title", "source_filename"]
    readonly_fields = ["created_at"]
    inlines = [BookingImportRowInline]


@admin.register(OpeningPaymentRecord)
class OpeningPaymentRecordAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "booking",
        "booking_import",
        "amount_inr",
        "payment_reference",
        "occurred_at",
    ]
    list_filter = ["occurred_at"]
    search_fields = [
        "booking__booking_contact_name",
        "booking__booking_contact_phone",
        "payment_reference",
        "note",
    ]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(BookingAdjustment)
class BookingAdjustmentAdmin(admin.ModelAdmin):
    list_display = ["id", "booking", "amount_inr", "recorded_by", "occurred_at"]
    list_filter = ["occurred_at"]
    search_fields = [
        "booking__booking_contact_name",
        "booking__booking_contact_phone",
        "adjustment_reason",
    ]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(RefundRecord)
class RefundRecordAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "booking",
        "amount_inr",
        "refund_reference",
        "recorded_by",
        "occurred_at",
    ]
    list_filter = ["occurred_at"]
    search_fields = [
        "booking__booking_contact_name",
        "booking__booking_contact_phone",
        "refund_reference",
        "refund_reason",
    ]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(LedgerEntry)
class LedgerEntryAdmin(admin.ModelAdmin):
    list_display = ["id", "booking", "entry_type", "amount_inr", "currency", "occurred_at"]
    list_filter = ["entry_type", "currency", "occurred_at"]
    search_fields = [
        "booking__booking_contact_name",
        "booking__booking_contact_phone",
        "description",
    ]


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "booking",
        "notification_type",
        "channel",
        "recipient_type",
        "recipient_name",
        "status",
        "sent_at",
    ]
    list_filter = ["notification_type", "channel", "recipient_type", "status", "sent_at"]
    search_fields = [
        "booking__booking_contact_name",
        "recipient_name",
        "recipient_phone",
        "recipient_email",
        "subject",
    ]
    readonly_fields = ["idempotency_key", "created_at", "updated_at"]


@admin.register(BookingAccessLink)
class BookingAccessLinkAdmin(admin.ModelAdmin):
    list_display = ["id", "booking", "scope", "traveler_slot", "expires_at", "revoked_at"]
    list_filter = ["scope", "expires_at", "revoked_at"]
    search_fields = ["booking__booking_contact_name", "booking__booking_contact_phone"]
    readonly_fields = ["token_digest", "created_at", "updated_at"]


@admin.register(TravelerDocument)
class TravelerDocumentAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "traveler_slot",
        "document_kind",
        "label",
        "document_state",
        "submitted_at",
        "reviewed_at",
    ]
    list_filter = ["document_kind", "document_state", "submitted_at", "reviewed_at"]
    search_fields = [
        "label",
        "original_filename",
        "traveler_slot__traveler_full_name",
        "traveler_slot__booking__booking_contact_name",
    ]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ["id", "organizer", "trip", "booking", "action", "actor", "occurred_at"]
    list_filter = ["action", "occurred_at"]
    search_fields = [
        "booking__booking_contact_name",
        "traveler_slot__traveler_full_name",
        "traveler_document__label",
    ]
    readonly_fields = ["created_at"]
