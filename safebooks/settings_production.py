"""Opt-in production settings: DJANGO_SETTINGS_MODULE=safebooks.settings_production.

All workers must receive identical hosting secrets and the same PostgreSQL and
Redis services. Missing or unsafe configuration prevents startup.
"""

import os
import re
from email.utils import parseaddr
from urllib.parse import urlsplit

from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.core.validators import validate_email

# Also protects explicit module imports (not only manage.py --settings).
os.environ["DJANGO_SETTINGS_MODULE"] = "safebooks.settings_production"
from .settings import *  # noqa: F403,E402


def _required(name):
    value = os.environ.get(name, "").strip()
    if not value:
        raise ImproperlyConfigured(f"Production requires {name} in hosting environment secrets.")
    return value


def _boolean(name, default=False):
    raw = os.environ.get(name, "true" if default else "false").strip().lower()
    if raw not in {"true", "false", "1", "0", "yes", "no", "on", "off"}:
        raise ImproperlyConfigured(f"{name} must be a boolean.")
    return raw in {"true", "1", "yes", "on"}


def _integer(name, default, *, minimum=1, maximum=86400):
    try:
        value = int(os.environ.get(name, str(default)))
    except (ValueError, TypeError):
        raise ImproperlyConfigured(f"{name} must be an integer.") from None
    if not minimum <= value <= maximum:
        raise ImproperlyConfigured(f"{name} is outside its supported range.")
    return value


DEBUG = False
if _boolean("SAFEBOOKS_DEBUG"):
    raise ImproperlyConfigured("Production cannot enable SAFEBOOKS_DEBUG.")

SECRET_KEY = _required("SAFEBOOKS_SECRET_KEY")
if len(SECRET_KEY) < 50 or len(set(SECRET_KEY)) < 5 or SECRET_KEY.startswith("django-insecure-"):
    raise ImproperlyConfigured("SAFEBOOKS_SECRET_KEY must be a strong, random production key.")

ALLOWED_HOSTS = [host.strip().lower() for host in _required("SAFEBOOKS_ALLOWED_HOSTS").split(",")]
if any(not re.fullmatch(r"[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?", host) or ".." in host for host in ALLOWED_HOSTS):
    raise ImproperlyConfigured("SAFEBOOKS_ALLOWED_HOSTS must contain exact hostnames or IPv4 addresses, without wildcards, schemes, paths, or ports.")

CSRF_TRUSTED_ORIGINS = [f"https://{host}" for host in ALLOWED_HOSTS]
if os.environ.get("SAFEBOOKS_CSRF_TRUSTED_ORIGINS", "").strip():
    CSRF_TRUSTED_ORIGINS = [origin.strip() for origin in os.environ["SAFEBOOKS_CSRF_TRUSTED_ORIGINS"].split(",")]
    for origin in CSRF_TRUSTED_ORIGINS:
        try:
            parsed = urlsplit(origin)
            valid = parsed.scheme == "https" and parsed.hostname in ALLOWED_HOSTS and parsed.netloc == parsed.hostname
        except ValueError:
            valid = False
        if not valid or parsed.path or parsed.query or parsed.fragment:
            raise ImproperlyConfigured("SAFEBOOKS_CSRF_TRUSTED_ORIGINS must contain HTTPS origins matching exact allowed hosts, without paths or wildcards.")

USE_POSTGRESQL = True
if not _boolean("SAFEBOOKS_USE_POSTGRESQL", True):
    raise ImproperlyConfigured("Production requires PostgreSQL, not local SQLite.")
_sslmode = os.environ.get("SAFEBOOKS_DB_SSLMODE", "require").strip()
if _sslmode not in {"require", "verify-ca", "verify-full"}:
    raise ImproperlyConfigured("Production PostgreSQL must use require, verify-ca, or verify-full SSL mode.")
_db_options = {"sslmode": _sslmode, "connect_timeout": 10}
if os.environ.get("SAFEBOOKS_DB_SSLROOTCERT", "").strip():
    _db_options["sslrootcert"] = os.environ["SAFEBOOKS_DB_SSLROOTCERT"].strip()
DATABASES = {"default": {
    "ENGINE": "django.db.backends.postgresql",
    "NAME": _required("SAFEBOOKS_DB_NAME"),
    "USER": _required("SAFEBOOKS_DB_USER"),
    "PASSWORD": _required("SAFEBOOKS_DB_PASSWORD"),
    "HOST": _required("SAFEBOOKS_DB_HOST"),
    "PORT": _integer("SAFEBOOKS_DB_PORT", 5432, maximum=65535),
    "OPTIONS": _db_options,
    "CONN_MAX_AGE": _integer("SAFEBOOKS_DB_CONN_MAX_AGE", 60, minimum=0, maximum=600),
    "CONN_HEALTH_CHECKS": True,
}}

_redis_url = _required("SAFEBOOKS_REDIS_URL")
try:
    _redis_parts = urlsplit(_redis_url)
    _redis_valid = (
        _redis_parts.scheme == "rediss" and bool(_redis_parts.hostname) and bool(_redis_parts.password)
        and not _redis_parts.query and not _redis_parts.fragment
        and not any(char in _redis_url for char in ";,\r\n")
        and (_redis_parts.port is None or 1 <= _redis_parts.port <= 65535)
        and re.fullmatch(r"/\d*", _redis_parts.path or "/")
    )
except ValueError:
    _redis_valid = False
if not _redis_valid:
    raise ImproperlyConfigured("SAFEBOOKS_REDIS_URL must be one TLS rediss:// endpoint with authentication, without query overrides or replicas.")
_cache_prefix = _required("SAFEBOOKS_CACHE_KEY_PREFIX")
if not re.fullmatch(r"[a-zA-Z0-9_-]{1,80}", _cache_prefix):
    raise ImproperlyConfigured("SAFEBOOKS_CACHE_KEY_PREFIX must be a short environment-specific identifier.")
CACHES = {"default": {
    "BACKEND": "django.core.cache.backends.redis.RedisCache",
    "LOCATION": _redis_url,
    "KEY_PREFIX": _cache_prefix,
    "TIMEOUT": 300,
    "OPTIONS": {
        "serializer": "safebooks.cache.AuthStateJSONSerializer",
        "socket_connect_timeout": 3,
        "socket_timeout": 3,
        "max_connections": 20,
        "ssl_cert_reqs": "required",
    },
}}
# Keep sessions durable in the shared database, not cookies or a volatile cache.
SESSION_ENGINE = "django.contrib.sessions.backends.db"
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
# Existing AJAX code reads the CSRF cookie; do not make it HttpOnly.
CSRF_COOKIE_HTTPONLY = False
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_SSL_REDIRECT = True
for _flag in ("SAFEBOOKS_SESSION_COOKIE_SECURE", "SAFEBOOKS_CSRF_COOKIE_SECURE", "SAFEBOOKS_SECURE_SSL_REDIRECT"):
    if not _boolean(_flag, True):
        raise ImproperlyConfigured(f"Production cannot disable {_flag}.")
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https") if _boolean("SAFEBOOKS_TRUST_PROXY_PROTO") else None
USE_X_FORWARDED_HOST = False
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"
# Do not enable persistent HSTS until the chosen host's HTTPS behavior is tested.
SECURE_HSTS_SECONDS = 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MIDDLEWARE = list(MIDDLEWARE)
MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}
WHITENOISE_USE_FINDERS = False
WHITENOISE_AUTOREFRESH = False

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
_requested_email_backend = os.environ.get("SAFEBOOKS_EMAIL_BACKEND", "") or os.environ.get("EMAIL_BACKEND", "")
if _requested_email_backend and _requested_email_backend != EMAIL_BACKEND:
    raise ImproperlyConfigured("Production must use SMTP, not a console/file/dummy email backend.")
EMAIL_HOST = _required("SAFEBOOKS_EMAIL_HOST")
EMAIL_HOST_USER = _required("SAFEBOOKS_EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = _required("SAFEBOOKS_EMAIL_HOST_PASSWORD")
EMAIL_USE_TLS = _boolean("SAFEBOOKS_EMAIL_USE_TLS", True)
EMAIL_USE_SSL = _boolean("SAFEBOOKS_EMAIL_USE_SSL")
if EMAIL_USE_TLS == EMAIL_USE_SSL:
    raise ImproperlyConfigured("Production SMTP must enable exactly one of TLS or SSL.")
EMAIL_PORT = _integer("SAFEBOOKS_EMAIL_PORT", 465 if EMAIL_USE_SSL else 587, maximum=65535)
EMAIL_TIMEOUT = _integer("SAFEBOOKS_EMAIL_TIMEOUT_SECONDS", 10, maximum=60)
DEFAULT_FROM_EMAIL = _required("SAFEBOOKS_DEFAULT_FROM_EMAIL")
try:
    validate_email(parseaddr(DEFAULT_FROM_EMAIL)[1])
except (ValidationError, ValueError):
    raise ImproperlyConfigured("SAFEBOOKS_DEFAULT_FROM_EMAIL must be a valid sender address.") from None
if "\r" in DEFAULT_FROM_EMAIL or "\n" in DEFAULT_FROM_EMAIL:
    raise ImproperlyConfigured("SAFEBOOKS_DEFAULT_FROM_EMAIL cannot contain newlines.")

_google_configured = bool(SAFEBOOKS_GOOGLE_OAUTH_CLIENT_ID or SAFEBOOKS_GOOGLE_OAUTH_CLIENT_SECRET or SAFEBOOKS_GOOGLE_OAUTH_REDIRECT_URI)
if _google_configured:
    for _name in ("SAFEBOOKS_GOOGLE_OAUTH_CLIENT_ID", "SAFEBOOKS_GOOGLE_OAUTH_CLIENT_SECRET", "SAFEBOOKS_GOOGLE_OAUTH_REDIRECT_URI"):
        _required(_name)
    try:
        _callback = urlsplit(SAFEBOOKS_GOOGLE_OAUTH_REDIRECT_URI)
        _callback_valid = _callback.scheme == "https" and _callback.netloc in ALLOWED_HOSTS and _callback.path == "/auth/google/callback/" and not _callback.query and not _callback.fragment
    except ValueError:
        _callback_valid = False
    if not _callback_valid:
        raise ImproperlyConfigured("Google OAuth redirect URI must be the HTTPS /auth/google/callback/ URL on an allowed host.")

LOGGING = {
    "version": 1, "disable_existing_loggers": False,
    "formatters": {"standard": {"format": "{levelname} {name}: {message}", "style": "{"}},
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "standard"}},
    "root": {"handlers": ["console"], "level": "WARNING"},
    "loggers": {
        "django": {"handlers": ["console"], "level": "WARNING", "propagate": False},
        "safebooks": {"handlers": ["console"], "level": "INFO", "propagate": False},
    },
}

SAFEBOOKS_BOOKKEEPER_TWO_FACTOR_LOGIN_TIMEOUT_SECONDS = _integer("SAFEBOOKS_BOOKKEEPER_TWO_FACTOR_LOGIN_TIMEOUT_SECONDS", 300)
SAFEBOOKS_BOOKKEEPER_TWO_FACTOR_LOGIN_MAX_ATTEMPTS = _integer("SAFEBOOKS_BOOKKEEPER_TWO_FACTOR_LOGIN_MAX_ATTEMPTS", 5, maximum=20)
SAFEBOOKS_BOOKKEEPER_TWO_FACTOR_LOGIN_LOCKOUT_SECONDS = _integer("SAFEBOOKS_BOOKKEEPER_TWO_FACTOR_LOGIN_LOCKOUT_SECONDS", 300)
SAFEBOOKS_ADMIN_TWO_FACTOR_LOGIN_TIMEOUT_SECONDS = _integer("SAFEBOOKS_ADMIN_TWO_FACTOR_LOGIN_TIMEOUT_SECONDS", 300)
SAFEBOOKS_ADMIN_TWO_FACTOR_LOGIN_MAX_ATTEMPTS = _integer("SAFEBOOKS_ADMIN_TWO_FACTOR_LOGIN_MAX_ATTEMPTS", 5, maximum=20)
SAFEBOOKS_ADMIN_TWO_FACTOR_LOGIN_LOCKOUT_SECONDS = _integer("SAFEBOOKS_ADMIN_TWO_FACTOR_LOGIN_LOCKOUT_SECONDS", 300)
