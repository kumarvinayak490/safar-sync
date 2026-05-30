from __future__ import annotations

import importlib
import inspect
import tomllib
from pathlib import Path

from django.apps import apps
from django.conf import settings
from django.db import models as django_models

TARGET_DOMAIN_APPS = (
    "organizers",
    "organizer_profile",
    "organizer_media",
    "organizer_policies",
    "team_access",
    "organizer_payments",
    "creative_setup",
    "trips",
    "trip_bookings",
    "trip_travelers",
    "trip_payments",
    "trip_operations",
    "public_discovery",
    "internal_admin",
)

LEGACY_COMPATIBILITY_IMPORTS = (
    (
        "organizers.booking_intake",
        "trip_bookings.intake",
        "BookingIntake",
    ),
    (
        "organizers.bookings.operations",
        "trip_bookings.operations",
        "confirm_booking",
    ),
    (
        "organizers.bookings.intake",
        "trip_bookings.intake",
        "prepare_manual_booking_intake",
    ),
    (
        "organizers.booking_operations_workflow",
        "trip_bookings.operations",
        "confirm_booking",
    ),
    (
        "organizers.financial_ledger",
        "trip_payments.financial_ledger",
        "FinancialLedger",
    ),
    (
        "organizers.payments.financial_ledger",
        "trip_payments.financial_ledger",
        "FinancialLedger",
    ),
    (
        "organizers.online_payment_readiness",
        "organizer_payments.online_payment_readiness",
        "OnlinePaymentReadinessDecision",
    ),
    (
        "organizers.payments.online_payment_readiness",
        "organizer_payments.online_payment_readiness",
        "OnlinePaymentReadinessDecision",
    ),
    (
        "organizers.operations_dashboard",
        "organizers.operations.dashboard",
        "build_operations_dashboard_payload",
    ),
    (
        "organizers.organizer_identity",
        "organizer_profile.identity",
        "organizer_identity_payload",
    ),
    (
        "organizers.organizer_invitations",
        "team_access.invitations",
        "create_organizer_invitation",
    ),
    (
        "organizers.team_access.invitations",
        "team_access.invitations",
        "create_organizer_invitation",
    ),
    (
        "organizers.permissions",
        "team_access.permissions",
        "require_membership",
    ),
    (
        "organizers.payment_setup_guidance",
        "organizers.payments.payment_setup_guidance",
        "individual_creator_payment_path_payload",
    ),
    (
        "organizers.payment_setup_readiness",
        "organizer_payments.payment_setup_readiness",
        "payment_setup_status_payload",
    ),
    (
        "organizers.payments.payment_setup_readiness",
        "organizer_payments.payment_setup_readiness",
        "payment_setup_status_payload",
    ),
    (
        "organizers.payments.manual_payment_instructions",
        "organizer_payments.manual_payment_instructions",
        "manual_payment_instructions_payload",
    ),
    (
        "organizers.payments.provider_account_readiness",
        "organizer_payments.provider_account_readiness",
        "ReadinessRegressionResult",
    ),
    (
        "organizers.platform_fees",
        "trip_payments.platform_fees",
        "refresh_platform_fee_statement",
    ),
    (
        "organizers.payments.platform_fees",
        "trip_payments.platform_fees",
        "refresh_platform_fee_statement",
    ),
    (
        "organizers.provider_adapters",
        "trip_payments.provider_adapters",
        "ProviderCheckoutRequest",
    ),
    (
        "organizers.payments.provider_adapters",
        "trip_payments.provider_adapters",
        "ProviderCheckoutRequest",
    ),
    (
        "organizers.provider_adapters",
        "organizer_payments.provider_adapters",
        "ProviderOAuthTokenExchangeResult",
    ),
    (
        "organizers.payments.provider_adapters",
        "organizer_payments.provider_adapters",
        "ProviderOAuthTokenExchangeResult",
    ),
    (
        "organizers.provider_authorization",
        "organizer_payments.provider_authorization",
        "start_provider_authorization",
    ),
    (
        "organizers.payments.provider_authorization",
        "organizer_payments.provider_authorization",
        "start_provider_authorization",
    ),
    (
        "organizers.provider_connection_tests",
        "organizer_payments.provider_connection_tests",
        "ProviderConnectionTestValidation",
    ),
    (
        "organizers.payments.provider_connection_tests",
        "organizer_payments.provider_connection_tests",
        "ProviderConnectionTestValidation",
    ),
    (
        "organizers.provider_credentials",
        "organizer_payments.provider_credentials",
        "SensitiveProviderCredentialStore",
    ),
    (
        "organizers.payments.provider_credentials",
        "organizer_payments.provider_credentials",
        "SensitiveProviderCredentialStore",
    ),
    (
        "organizers.provider_payment_lifecycle",
        "trip_payments.provider_payment_lifecycle",
        "ProviderCheckoutSession",
    ),
    (
        "organizers.payments.provider_payment_lifecycle",
        "trip_payments.provider_payment_lifecycle",
        "ProviderCheckoutSession",
    ),
    (
        "organizers.provider_webhooks",
        "trip_payments.provider_webhooks",
        "process_razorpay_webhook",
    ),
    (
        "organizers.payments.provider_webhooks",
        "trip_payments.provider_webhooks",
        "process_razorpay_webhook",
    ),
    (
        "organizers.public_booking_gate",
        "trips.booking_availability",
        "public_booking_gate_decision",
    ),
    (
        "organizers.payments.public_booking_gate",
        "trips.booking_availability",
        "public_booking_gate_decision",
    ),
    (
        "organizers.payments.payment_method_readiness",
        "trips.payment_method_readiness",
        "payment_method_readiness_for_trip",
    ),
    (
        "organizers.rich_text",
        "trips.rich_text",
        "default_trip_rich_text",
    ),
    (
        "organizers.trip_profile.rich_text",
        "trips.rich_text",
        "default_trip_rich_text",
    ),
    (
        "organizers.seat_holds",
        "trip_payments.seat_holds",
        "create_seat_hold_for_payment_attempt",
    ),
    (
        "organizers.payments.seat_holds",
        "trip_payments.seat_holds",
        "create_seat_hold_for_payment_attempt",
    ),
    (
        "organizers.session_onboarding",
        "organizers.onboarding.session",
        "session_onboarding_payload",
    ),
    (
        "organizers.traveler_readiness",
        "trip_travelers.readiness",
        "TravelerReadiness",
    ),
    (
        "organizers.travelers.readiness",
        "trip_travelers.readiness",
        "TravelerReadiness",
    ),
    (
        "organizers.trip_overview",
        "organizers.operations.trip_overview",
        "build_trip_overview_payload",
    ),
    (
        "organizers.trip_profile_activity",
        "trips.activity",
        "record_public_trip_page_published",
    ),
    (
        "organizers.trip_profile_lock",
        "trips.locks",
        "is_trip_profile_locked",
    ),
    (
        "organizers.trip_profile.locks",
        "trips.locks",
        "is_trip_profile_locked",
    ),
    (
        "organizers.trip_profile_publication_readiness",
        "trips.publication_readiness",
        "trip_profile_publication_readiness",
    ),
    (
        "organizers.services",
        "trip_operations.activity",
        "record_activity_log",
    ),
    (
        "organizers.serializers",
        "trip_operations.serializers",
        "ActivityLogSerializer",
    ),
)

LEGACY_MODEL_EXPORTS = (
    ("team_access.models", "OrganizerMembership"),
    ("team_access.models", "OrganizerInvitation"),
    ("organizer_payments.models", "ProviderPaymentSetup"),
    ("organizer_payments.models", "PayoutAccount"),
    ("organizer_payments.models", "ManualPaymentInstructions"),
    ("trips.models", "Trip"),
    ("trips.models", "TripPackage"),
    ("trips.models", "TripItineraryDay"),
    ("trip_bookings.models", "Booking"),
    ("trip_bookings.models", "BookingAccessLink"),
    ("trip_travelers.models", "TravelerSlot"),
    ("trip_travelers.models", "TravelerDocument"),
    ("trip_payments.models", "PaymentAttempt"),
    ("trip_payments.models", "SeatHold"),
    ("trip_payments.models", "ProviderPayment"),
    ("trip_payments.models", "ProviderWebhookEvent"),
    ("trip_payments.models", "PaymentException"),
    ("trip_payments.models", "ManualPayment"),
    ("trip_operations.models", "ActivityLog"),
    ("trip_operations.models", "Notification"),
)

ORGANIZER_ROOT_INTEGRATION_MODULES = {
    "__init__.py",
    "admin.py",
    "apps.py",
    "models.py",
    "permissions.py",
    "serializers.py",
    "services.py",
    "signals.py",
    "urls.py",
    "views.py",
}

ORGANIZER_ROOT_COMPATIBILITY_MODULES = {
    f"{legacy_path.rsplit('.', maxsplit=1)[-1]}.py"
    for legacy_path, _owner_path, _symbol_name in LEGACY_COMPATIBILITY_IMPORTS
}


def test_target_domain_apps_are_registered_and_importable():
    installed_app_names = {app_config.name for app_config in apps.get_app_configs()}

    assert list(settings.DATABASES) == ["default"]
    for app_name in TARGET_DOMAIN_APPS:
        assert app_name in installed_app_names
        importlib.import_module(app_name)
        importlib.import_module(f"{app_name}.apps")
        importlib.import_module(f"{app_name}.migrations")


def test_package_discovery_includes_target_domain_apps():
    pyproject_path = Path(__file__).resolve().parents[1] / "pyproject.toml"
    pyproject = tomllib.loads(pyproject_path.read_text())
    package_includes = pyproject["tool"]["setuptools"]["packages"]["find"]["include"]

    for app_name in TARGET_DOMAIN_APPS:
        assert f"{app_name}*" in package_includes


def test_legacy_organizer_module_imports_reexport_current_owners():
    for legacy_path, owner_path, symbol_name in LEGACY_COMPATIBILITY_IMPORTS:
        legacy_module = importlib.import_module(legacy_path)
        owner_module = importlib.import_module(owner_path)

        assert getattr(legacy_module, symbol_name) is getattr(owner_module, symbol_name)


def test_legacy_organizer_model_exports_reexport_domain_models():
    legacy_models = importlib.import_module("organizers.models")

    for owner_path, symbol_name in LEGACY_MODEL_EXPORTS:
        owner_module = importlib.import_module(owner_path)

        assert getattr(legacy_models, symbol_name) is getattr(owner_module, symbol_name)


def test_organizer_root_models_define_only_the_aggregate_root():
    legacy_models = importlib.import_module("organizers.models")
    locally_defined_models = {
        name
        for name, value in inspect.getmembers(legacy_models, inspect.isclass)
        if issubclass(value, django_models.Model) and value.__module__ == legacy_models.__name__
    }

    assert locally_defined_models == {"Organizer"}


def test_organizer_root_top_level_modules_are_integration_or_compatibility():
    organizer_root = Path(__file__).resolve().parents[1] / "organizers"
    root_modules = {path.name for path in organizer_root.glob("*.py")}

    assert root_modules <= ORGANIZER_ROOT_INTEGRATION_MODULES | ORGANIZER_ROOT_COMPATIBILITY_MODULES
