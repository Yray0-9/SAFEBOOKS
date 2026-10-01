import logging
import re
from urllib.parse import urlsplit

from django.conf import settings
from django.core.cache import cache
from django.core.mail import get_connection, send_mail
from django.utils import timezone


logger = logging.getLogger(__name__)

CATEGORY_LABELS = {
    "suggestion": "Suggestion or feature idea",
    "confusing": "Something is confusing",
    "bug": "Bug or unexpected behavior",
    "comment": "General comment or compliment",
}

MIN_MESSAGE_LENGTH = 10
MAX_MESSAGE_LENGTH = 2000
MAX_PAGE_TITLE_LENGTH = 120
MAX_PAGE_PATH_LENGTH = 300


def is_feedback_feature_available() -> bool:
    return bool(
        getattr(settings, "SAFEBOOKS_FEEDBACK_ENABLED", False)
        and str(getattr(settings, "SAFEBOOKS_FEEDBACK_RECIPIENT_EMAIL", "") or "").strip()
    )


def _result(ok: bool, message: str, *, code: str = "") -> dict:
    return {
        "ok": ok,
        "message": message,
        "code": code,
    }


def _normalize_single_line(value, maximum_length: int) -> str:
    normalized = re.sub(r"\s+", " ", str(value or "")).strip()
    return normalized[:maximum_length]


def _normalize_page_path(value) -> str | None:
    raw_path = str(value or "").strip()
    if not raw_path or len(raw_path) > MAX_PAGE_PATH_LENGTH:
        return None

    parsed = urlsplit(raw_path)
    if parsed.scheme or parsed.netloc:
        return None

    path = parsed.path or ""
    if not path.startswith("/") or path.startswith("//"):
        return None

    return path[:MAX_PAGE_PATH_LENGTH]


def _consume_rate_limit(bookkeeper_id: int) -> bool:
    maximum = max(1, int(getattr(settings, "SAFEBOOKS_FEEDBACK_RATE_LIMIT_COUNT", 5)))
    window_seconds = max(
        1,
        int(getattr(settings, "SAFEBOOKS_FEEDBACK_RATE_LIMIT_WINDOW_SECONDS", 10 * 60)),
    )
    cache_key = f"safebooks:feedback-submissions:{bookkeeper_id}"

    if cache.add(cache_key, 1, timeout=window_seconds):
        return True

    try:
        current_count = cache.incr(cache_key)
    except ValueError:
        cache.set(cache_key, 1, timeout=window_seconds)
        current_count = 1

    return current_count <= maximum


def _build_email_body(bookkeeper, *, category_label: str, message: str, page_title: str, page_path: str) -> str:
    submitted_at = timezone.localtime(timezone.now()).strftime("%B %d, %Y, %I:%M %p")
    return (
        "SafeBooks Remote Beta Feedback\n\n"
        f"Submitted by: {bookkeeper.full_name}\n"
        f"Username: {bookkeeper.username}\n"
        f"Registered email: {bookkeeper.email}\n"
        f"Submitted at: {submitted_at} (Asia/Manila)\n\n"
        f"Category: {category_label}\n"
        f"Page: {page_title}\n"
        f"Path: {page_path}\n\n"
        "Message:\n"
        f"{message}\n"
    )


def submit_bookkeeper_feedback(bookkeeper, payload: dict) -> dict:
    if not is_feedback_feature_available():
        return _result(
            False,
            "Feedback is temporarily unavailable.",
            code="feature_unavailable",
        )

    category = str(payload.get("category") or "").strip().lower()
    category_label = CATEGORY_LABELS.get(category)
    if category_label is None:
        return _result(False, "Select a valid feedback category.", code="invalid_category")

    message = str(payload.get("message") or "").strip()
    if len(message) < MIN_MESSAGE_LENGTH:
        return _result(
            False,
            f"Feedback must be at least {MIN_MESSAGE_LENGTH} characters.",
            code="invalid_message",
        )
    if len(message) > MAX_MESSAGE_LENGTH:
        return _result(
            False,
            f"Feedback must be {MAX_MESSAGE_LENGTH} characters or fewer.",
            code="invalid_message",
        )

    page_title = _normalize_single_line(payload.get("page_title"), MAX_PAGE_TITLE_LENGTH)
    if not page_title:
        page_title = "SafeBooks page"

    page_path = _normalize_page_path(payload.get("page_path"))
    if page_path is None:
        return _result(False, "Invalid page context.", code="invalid_page_context")

    if not _consume_rate_limit(bookkeeper.id):
        return _result(
            False,
            "Too many feedback messages were sent. Please try again later.",
            code="rate_limited",
        )

    display_name = _normalize_single_line(
        bookkeeper.full_name or bookkeeper.username or "Bookkeeper",
        80,
    )
    recipient = str(settings.SAFEBOOKS_FEEDBACK_RECIPIENT_EMAIL or "").strip()
    subject = f"[SafeBooks Beta Feedback] {category_label} from {display_name}"
    email_body = _build_email_body(
        bookkeeper,
        category_label=category_label,
        message=message,
        page_title=page_title,
        page_path=page_path,
    )

    timeout_seconds = max(
        1,
        int(getattr(settings, "SAFEBOOKS_FEEDBACK_EMAIL_TIMEOUT_SECONDS", 10)),
    )

    try:
        connection = get_connection(timeout=timeout_seconds)
        sent_count = send_mail(
            subject,
            email_body,
            settings.DEFAULT_FROM_EMAIL,
            [recipient],
            fail_silently=False,
            connection=connection,
        )
    except Exception:
        logger.warning(
            "Failed to deliver beta feedback for bookkeeper %s.",
            bookkeeper.id,
            exc_info=True,
        )
        return _result(
            False,
            "We could not send your feedback right now. Please try again.",
            code="delivery_failed",
        )

    if sent_count < 1:
        logger.warning(
            "The email backend did not confirm beta feedback delivery for bookkeeper %s.",
            bookkeeper.id,
        )
        return _result(
            False,
            "We could not send your feedback right now. Please try again.",
            code="delivery_failed",
        )

    return _result(
        True,
        "Thank you - your feedback was sent to the SafeBooks developer.",
    )
