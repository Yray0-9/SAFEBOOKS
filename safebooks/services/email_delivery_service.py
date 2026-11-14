"""Delivery acknowledgement is not proof of receipt in an inbox."""
from django.conf import settings


LOCAL_EMAIL_BACKENDS = {
    "django.core.mail.backends.console.EmailBackend",
    "django.core.mail.backends.filebased.EmailBackend",
    "django.core.mail.backends.locmem.EmailBackend",
    "django.core.mail.backends.dummy.EmailBackend",
}
PREVIEW_ONLY_EMAIL_BACKENDS = LOCAL_EMAIL_BACKENDS - {"django.core.mail.backends.locmem.EmailBackend"}


def email_count_confirmed(count):
    return isinstance(count, int) and not isinstance(count, bool) and count > 0


def email_delivery_hint():
    if settings.EMAIL_BACKEND in LOCAL_EMAIL_BACKENDS:
        return "This environment uses a local/test email backend. Emails will not reach inboxes."
    return "Email is attempted through the configured service. Acceptance does not guarantee inbox delivery."


def preview_only_email_backend():
    return settings.EMAIL_BACKEND in PREVIEW_ONLY_EMAIL_BACKENDS
