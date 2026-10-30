"""
Django settings for the FitVision project.

Configuration is read from environment variables (loaded from backend/.env in
development). See `.env.example` for the full list of supported variables.
"""

import os
from datetime import timedelta
from importlib.util import find_spec
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# Allow users to override the Hugging Face endpoint without editing this file.
os.environ.setdefault("HF_ENDPOINT", os.getenv("HF_ENDPOINT", "https://hf-mirror.com"))


def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_list(name: str, default: str = "") -> list[str]:
    raw = os.getenv(name, default)
    return [item.strip() for item in raw.split(",") if item.strip()]


# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------
DEBUG = env_bool("DEBUG", True)

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    if not DEBUG:
        raise ImproperlyConfigured("SECRET_KEY must be set when DEBUG=False")
    # Ephemeral development key; never use it in production.
    SECRET_KEY = "django-insecure-dev-only-do-not-use-in-production"

ALLOWED_HOSTS = env_list("ALLOWED_HOSTS", "127.0.0.1,localhost")
if DEBUG and not ALLOWED_HOSTS:
    ALLOWED_HOSTS = ["127.0.0.1", "localhost"]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "corsheaders",
    "users",
    "ai_models",
    "analytics",
    "exercises",
    "training",
    "recommendations",
    "drf_spectacular",
    "django_filters",
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

# WhiteNoise serves static files in production deployments. It is optional in
# local development so a minimal `pip install` can still run the project.
if find_spec("whitenoise"):
    MIDDLEWARE.insert(2, "whitenoise.middleware.WhiteNoiseMiddleware")

ROOT_URLCONF = "fitvision.urls"

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

WSGI_APPLICATION = "fitvision.wsgi.application"
ASGI_APPLICATION = "fitvision.asgi.application"

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
# PostgreSQL is used when DB_NAME is set; otherwise the project falls back to
# SQLite so that a fresh clone / CI can run without extra services.
DB_NAME = os.getenv("DB_NAME")
if os.getenv("DB_ENGINE", "").lower() == "sqlite" or not DB_NAME:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": DB_NAME,
            "USER": os.getenv("DB_USER", "postgres"),
            "PASSWORD": os.getenv("DB_PASSWORD", ""),
            "HOST": os.getenv("DB_HOST", "127.0.0.1"),
            "PORT": os.getenv("DB_PORT", "5432"),
            "OPTIONS": {"connect_timeout": 60},
            "CONN_MAX_AGE": 60 if not DEBUG else 0,
        }
    }

# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ---------------------------------------------------------------------------
# Internationalization
# ---------------------------------------------------------------------------
LANGUAGE_CODE = "zh-cn"
TIME_ZONE = "Asia/Shanghai"
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# Static & media files
# ---------------------------------------------------------------------------
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# VLM requests send base64 images; keep headroom over Django's 2.5 MB default.
DATA_UPLOAD_MAX_MEMORY_SIZE = int(os.getenv("DATA_UPLOAD_MAX_MEMORY_SIZE", 10 * 1024 * 1024))
FILE_UPLOAD_MAX_MEMORY_SIZE = int(os.getenv("FILE_UPLOAD_MAX_MEMORY_SIZE", 10 * 1024 * 1024))

# Reuse healthy DB connections in production.
CONN_HEALTH_CHECKS = True

if not DEBUG and find_spec("whitenoise"):
    STORAGES = {
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {
            "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"
        },
    }

# ---------------------------------------------------------------------------
# Django REST Framework
# ---------------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        # Session auth keeps the Django admin usable in the browser.
        "rest_framework.authentication.SessionAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    # Basic abuse protection. Tune via THROTTLE_* environment variables.
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": os.getenv("THROTTLE_ANON", "60/min"),
        "user": os.getenv("THROTTLE_USER", "600/min"),
        "auth": os.getenv("THROTTLE_AUTH", "10/min"),
    },
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(
        minutes=int(os.getenv("ACCESS_TOKEN_LIFETIME_MINUTES", 720))
    ),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=int(os.getenv("REFRESH_TOKEN_LIFETIME_DAYS", 7))),
    "UPDATE_LAST_LOGIN": True,
}

SPECTACULAR_SETTINGS = {
    "TITLE": "FitVision API",
    "DESCRIPTION": "FitVision — AI 健身教练平台 API 文档",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
CORS_ALLOW_ALL_ORIGINS = env_bool("CORS_ALLOW_ALL_ORIGINS", False)
CORS_ALLOWED_ORIGINS = env_list(
    "CORS_ALLOWED_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173,"
    "http://localhost:8080,http://127.0.0.1:8080",
)
CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS", "")

# ---------------------------------------------------------------------------
# Cache / Celery
# ---------------------------------------------------------------------------
REDIS_URL = os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")
CACHE_BACKEND = os.getenv("CACHE_BACKEND", "locmem").strip().lower()

if CACHE_BACKEND == "redis":
    CACHES = {
        "default": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": REDIS_URL,
            "OPTIONS": {"CLIENT_CLASS": "django_redis.client.DefaultClient"},
        }
    }
    SESSION_ENGINE = "django.contrib.sessions.backends.cache"
    SESSION_CACHE_ALIAS = "default"
else:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "fitvision-locmem",
        }
    }
    SESSION_ENGINE = "django.contrib.sessions.backends.db"

CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple": {"format": "[{levelname}] {asctime} {name}: {message}", "style": "{"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "simple"},
    },
    "root": {"handlers": ["console"], "level": LOG_LEVEL},
    "loggers": {
        # SQL query logging is opt-in via `LOG_LEVEL=DEBUG`.
        "django.db.backends": {"handlers": ["console"], "level": "WARNING", "propagate": False},
    },
}

# ---------------------------------------------------------------------------
# Security (production only)
# ---------------------------------------------------------------------------
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"

if not DEBUG:
    SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", True)
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# ---------------------------------------------------------------------------
# Error reporting (optional)
# ---------------------------------------------------------------------------
SENTRY_DSN = os.getenv("SENTRY_DSN")
if SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[DjangoIntegration()],
        traces_sample_rate=float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.1")),
        send_default_pii=False,
        environment=os.getenv("SENTRY_ENVIRONMENT", "production" if not DEBUG else "development"),
    )
