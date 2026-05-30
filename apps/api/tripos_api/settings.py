from __future__ import annotations

import os
from pathlib import Path

import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "unsafe-local-dev-secret")
TRIPOS_PROVIDER_CREDENTIAL_ENCRYPTION_KEY = os.getenv(
    "TRIPOS_PROVIDER_CREDENTIAL_ENCRYPTION_KEY",
    SECRET_KEY,
)
TRIPOS_PROVIDER_CREDENTIAL_ENCRYPTION_KEY_ID = os.getenv(
    "TRIPOS_PROVIDER_CREDENTIAL_ENCRYPTION_KEY_ID",
    "local",
)
TRIPOS_PROVIDER_AUTHORIZATION_STATE_SECONDS = int(
    os.getenv("TRIPOS_PROVIDER_AUTHORIZATION_STATE_SECONDS", "900")
)
TRIPOS_RAZORPAY_OAUTH_CLIENT_ID = os.getenv("TRIPOS_RAZORPAY_OAUTH_CLIENT_ID", "")
TRIPOS_RAZORPAY_OAUTH_CLIENT_SECRET = os.getenv("TRIPOS_RAZORPAY_OAUTH_CLIENT_SECRET", "")
TRIPOS_RAZORPAY_OAUTH_AUTHORIZE_URL = os.getenv(
    "TRIPOS_RAZORPAY_OAUTH_AUTHORIZE_URL",
    "https://auth.razorpay.com/authorize",
)
TRIPOS_RAZORPAY_OAUTH_TOKEN_URL = os.getenv(
    "TRIPOS_RAZORPAY_OAUTH_TOKEN_URL",
    "https://auth.razorpay.com/token",
)
TRIPOS_RAZORPAY_OAUTH_SCOPES = [
    scope.strip()
    for scope in os.getenv("TRIPOS_RAZORPAY_OAUTH_SCOPES", "read_write").split(",")
    if scope.strip()
]
TRIPOS_RAZORPAY_OAUTH_TIMEOUT_SECONDS = float(
    os.getenv("TRIPOS_RAZORPAY_OAUTH_TIMEOUT_SECONDS", "10")
)
TRIPOS_RAZORPAY_API_BASE_URL = os.getenv(
    "TRIPOS_RAZORPAY_API_BASE_URL",
    "https://api.razorpay.com/v1",
)
TRIPOS_RAZORPAY_API_TIMEOUT_SECONDS = float(os.getenv("TRIPOS_RAZORPAY_API_TIMEOUT_SECONDS", "10"))
TRIPOS_RAZORPAY_WEBHOOK_SECRET = os.getenv("TRIPOS_RAZORPAY_WEBHOOK_SECRET", "")
DEBUG = os.getenv("DJANGO_DEBUG", "false").lower() in {"1", "true", "yes", "on"}
ALLOWED_HOSTS = [
    host.strip()
    for host in os.getenv("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,testserver").split(",")
    if host.strip()
]

INSTALLED_APPS = [
    "corsheaders",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "health",
    "organizers.apps.OrganizersConfig",
    "organizer_profile.apps.OrganizerProfileConfig",
    "organizer_media.apps.OrganizerMediaConfig",
    "organizer_policies.apps.OrganizerPoliciesConfig",
    "team_access.apps.TeamAccessConfig",
    "organizer_payments.apps.OrganizerPaymentsConfig",
    "creative_setup.apps.CreativeSetupConfig",
    "trips.apps.TripsConfig",
    "trip_bookings.apps.TripBookingsConfig",
    "trip_travelers.apps.TripTravelersConfig",
    "trip_payments.apps.TripPaymentsConfig",
    "trip_operations.apps.TripOperationsConfig",
    "public_discovery.apps.PublicDiscoveryConfig",
    "internal_admin.apps.InternalAdminConfig",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

ROOT_URLCONF = "tripos_api.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "tripos_api.wsgi.application"

DATABASE_URL = os.getenv("DATABASE_URL", "postgres://tripos:tripos@localhost:5432/tripos")
DATABASES = {
    "default": dj_database_url.parse(
        DATABASE_URL,
        conn_max_age=60,
        conn_health_checks=True,
    )
}

CORS_ALLOW_CREDENTIALS = True

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
MEDIA_URL = "media/"
MEDIA_ROOT = os.getenv("DJANGO_MEDIA_ROOT", str(BASE_DIR / ".local" / "media"))
FILE_UPLOAD_PERMISSIONS = 0o640
FILE_UPLOAD_DIRECTORY_PERMISSIONS = 0o750
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
TRIPOS_SEAT_HOLD_SECONDS = int(os.getenv("TRIPOS_SEAT_HOLD_SECONDS", "600"))

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.BasicAuthentication",
    ],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser"],
}

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
OBJECT_STORAGE = {
    "endpoint_url": os.getenv("OBJECT_STORAGE_ENDPOINT_URL", "http://localhost:9000"),
    "bucket": os.getenv("OBJECT_STORAGE_BUCKET", "tripos-local"),
    "access_key_id": os.getenv("OBJECT_STORAGE_ACCESS_KEY_ID", "tripos"),
    "secret_access_key": os.getenv("OBJECT_STORAGE_SECRET_ACCESS_KEY", "tripos-local-secret"),
}
