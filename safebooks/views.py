import json
import logging
from functools import wraps
from hashlib import sha256
import secrets
from urllib.parse import urlencode, urlsplit

from django.conf import settings
from django.core.cache import cache
from django.db import DatabaseError, transaction
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import Resolver404, resolve, reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_http_methods, require_POST

from safebooks.models import AdminAccount, AdminAuditLog, BookkeeperAccount, BookkeeperAuditLog, Client
from safebooks.services.auth_service import (
    authenticate_google_bookkeeper,
    build_google_oauth_authorization_url,
    complete_google_signup,
    complete_bookkeeper_login,
    exchange_google_oauth_code,
    is_google_oauth_configured,
    login_user_or_admin,
    register_user,
    send_email_verification_code,
    verify_email_code,
)
from safebooks.services.client_service import (
    create_client_for_bookkeeper,
    delete_client_for_bookkeeper,
    get_client_for_bookkeeper,
    list_clients_for_bookkeeper,
    reopen_client_for_bookkeeper,
    resolve_client_remarks,
    update_client_for_bookkeeper,
)
from safebooks.services.financial_record_service import (
    create_record_for_client_period,
    delete_record_for_client,
    get_last_record_for_client_period,
    list_financial_clients_for_bookkeeper,
    list_records_for_client_period,
    list_transactions_for_client_range,
    list_transaction_years_for_client,
    update_record_for_client_period,
)
from safebooks.services.dashboard_service import get_dashboard_summary_for_bookkeeper
from safebooks.services.analytics_service import get_analytics_summary_for_bookkeeper
from safebooks.services.settings_service import (
    get_workspace_defaults_for_bookkeeper,
    update_client_record_email_notifications_preference,
    update_workspace_defaults_for_bookkeeper,
)
from safebooks.services.deactivation_request_service import (
    get_deactivation_request_status,
    request_bookkeeper_deactivation,
)
from safebooks.services.security_service import (
    change_bookkeeper_password,
    confirm_client_details_access,
    create_bookkeeper_two_factor_setup,
    disable_bookkeeper_two_factor,
    enable_bookkeeper_two_factor,
    get_bookkeeper_two_factor_status,
    update_client_details_access_preference,
    update_login_alerts_preference,
    verify_bookkeeper_two_factor_login,
)
from safebooks.services.profile_service import (
    get_profile_for_bookkeeper,
    update_profile_for_bookkeeper,
)
from safebooks.services.admin_approvals_service import (
    approve_bookkeeper,
    reject_bookkeeper,
    list_admin_approvals,
    retry_approval_decision_email,
)
from safebooks.services.admin_bookkeepers_service import (
    list_admin_bookkeepers,
    deactivate_bookkeeper,
    decline_deactivation_request,
    reactivate_bookkeeper,
    delete_bookkeeper_account,
)
from safebooks.services.admin_audit_service import list_admin_audit_logs, record_admin_auth_event
from safebooks.services.bookkeeper_audit_service import (
    list_bookkeeper_audit_logs,
    record_bookkeeper_audit,
)
from safebooks.services.admin_dashboard_service import get_admin_dashboard_summary
from safebooks.services.admin_profile_service import (
    change_admin_password,
    get_admin_profile,
    update_admin_profile,
)
from safebooks.services.admin_security_service import (
    create_admin_two_factor_setup,
    disable_admin_two_factor,
    enable_admin_two_factor,
    regenerate_admin_two_factor_recovery_codes,
    verify_admin_two_factor_login,
)
from safebooks.services.session_security_service import account_session_auth_hash, session_auth_hash_matches
from safebooks.services.email_delivery_service import email_delivery_hint
from safebooks.services.login_attempt_service import reserve_password_login

logger = logging.getLogger(__name__)


SESSION_BOOKKEEPER_ID_KEY = "safebooks_bookkeeper_id"
SESSION_BOOKKEEPER_AUTH_HASH_KEY = "safebooks_bookkeeper_auth_hash"
SESSION_BOOKKEEPER_TWO_FACTOR_SETUP_KEY = "safebooks_bookkeeper_two_factor_setup"
SESSION_BOOKKEEPER_TWO_FACTOR_CHALLENGE_KEY = "safebooks_bookkeeper_two_factor_challenge"
SESSION_ADMIN_ID_KEY = "safebooks_admin_id"
SESSION_ADMIN_AUTH_HASH_KEY = "safebooks_admin_auth_hash"
SESSION_ADMIN_AUTHENTICATED_AT_KEY = "safebooks_admin_authenticated_at"
SESSION_ADMIN_LAST_ACTIVITY_AT_KEY = "safebooks_admin_last_activity_at"
SESSION_ADMIN_TWO_FACTOR_SETUP_KEY = "safebooks_admin_two_factor_setup"
SESSION_ADMIN_TWO_FACTOR_CHALLENGE_KEY = "safebooks_admin_two_factor_challenge"
SESSION_CLIENT_DETAILS_VERIFIED_UNTIL_KEY = "safebooks_client_details_verified_until"
SESSION_CLIENT_PROFILE_ACCESS_KEY = "safebooks_client_profile_access"
SESSION_GOOGLE_OAUTH_STATE_KEY = "safebooks_google_oauth_state"
SESSION_GOOGLE_SIGNUP_PROFILE_KEY = "safebooks_google_signup_profile"
SESSION_PASSWORD_RESET_AUTHORIZATION_KEY = "safebooks_password_reset_authorization"
CLIENT_DETAILS_CONFIRMATION_WINDOW_SECONDS = 15 * 60


def _session_timestamp(value) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _clear_admin_session(request) -> None:
    for key in (
        SESSION_ADMIN_ID_KEY,
        SESSION_ADMIN_AUTH_HASH_KEY,
        SESSION_ADMIN_AUTHENTICATED_AT_KEY,
        SESSION_ADMIN_LAST_ACTIVITY_AT_KEY,
        SESSION_ADMIN_TWO_FACTOR_SETUP_KEY,
        SESSION_ADMIN_TWO_FACTOR_CHALLENGE_KEY,
    ):
        request.session.pop(key, None)
    request.session.modified = True


def _clear_bookkeeper_session(request) -> None:
    for key in (
        SESSION_BOOKKEEPER_ID_KEY, SESSION_BOOKKEEPER_AUTH_HASH_KEY,
        SESSION_BOOKKEEPER_TWO_FACTOR_SETUP_KEY, SESSION_BOOKKEEPER_TWO_FACTOR_CHALLENGE_KEY,
        SESSION_CLIENT_DETAILS_VERIFIED_UNTIL_KEY, SESSION_CLIENT_PROFILE_ACCESS_KEY,
    ):
        request.session.pop(key, None)


def _clear_authentication_state(request) -> None:
    _clear_admin_session(request)
    _clear_bookkeeper_session(request)
    request.session.pop(SESSION_PASSWORD_RESET_AUTHORIZATION_KEY, None)


def _renew_current_authenticated_session(request, account, *, admin=False) -> None:
    # The browser that just proved the security change remains usable; other
    # sessions retain their old proof and fail the next authorization check.
    request.session.cycle_key()
    auth_key = SESSION_ADMIN_AUTH_HASH_KEY if admin else SESSION_BOOKKEEPER_AUTH_HASH_KEY
    request.session[auth_key] = account_session_auth_hash(account)
    for key in (
        SESSION_CLIENT_DETAILS_VERIFIED_UNTIL_KEY, SESSION_CLIENT_PROFILE_ACCESS_KEY,
        SESSION_ADMIN_TWO_FACTOR_SETUP_KEY, SESSION_ADMIN_TWO_FACTOR_CHALLENGE_KEY,
        SESSION_BOOKKEEPER_TWO_FACTOR_SETUP_KEY, SESSION_BOOKKEEPER_TWO_FACTOR_CHALLENGE_KEY,
        SESSION_PASSWORD_RESET_AUTHORIZATION_KEY,
    ):
        request.session.pop(key, None)
    request.session.modified = True


def _admin_session_is_expired(request, now_timestamp: int) -> bool:
    authenticated_at = _session_timestamp(
        request.session.get(SESSION_ADMIN_AUTHENTICATED_AT_KEY)
    )
    last_activity_at = _session_timestamp(
        request.session.get(SESSION_ADMIN_LAST_ACTIVITY_AT_KEY)
    )

    # Preserve sessions created before this policy was deployed, then enforce
    # both limits from their first authenticated request onward.
    if authenticated_at <= 0 or authenticated_at > now_timestamp:
        authenticated_at = now_timestamp
        request.session[SESSION_ADMIN_AUTHENTICATED_AT_KEY] = authenticated_at
    if last_activity_at <= 0 or last_activity_at > now_timestamp:
        last_activity_at = now_timestamp
        request.session[SESSION_ADMIN_LAST_ACTIVITY_AT_KEY] = last_activity_at

    max_age = max(
        1,
        int(getattr(settings, "SAFEBOOKS_ADMIN_SESSION_MAX_AGE_SECONDS", 8 * 60 * 60)),
    )
    idle_timeout = max(
        1,
        int(getattr(settings, "SAFEBOOKS_ADMIN_SESSION_IDLE_TIMEOUT_SECONDS", 30 * 60)),
    )

    return (
        now_timestamp - authenticated_at >= max_age
        or now_timestamp - last_activity_at >= idle_timeout
    )


def _set_admin_session(request, account_id: AdminAccount | int, *, second_factor_verified=False) -> None:
    account = account_id if isinstance(account_id, AdminAccount) else AdminAccount.objects.get(id=account_id)
    account_id = account.id
    if account.two_factor_enabled and not second_factor_verified:
        raise ValueError("Admin second-factor verification is required.")
    now_timestamp = int(timezone.now().timestamp())
    request.session.cycle_key()
    _clear_authentication_state(request)
    request.session[SESSION_ADMIN_ID_KEY] = account_id
    request.session[SESSION_ADMIN_AUTH_HASH_KEY] = account_session_auth_hash(account)
    request.session[SESSION_ADMIN_AUTHENTICATED_AT_KEY] = now_timestamp
    request.session[SESSION_ADMIN_LAST_ACTIVITY_AT_KEY] = now_timestamp
    request.session.pop(SESSION_ADMIN_TWO_FACTOR_SETUP_KEY, None)
    request.session.pop(SESSION_ADMIN_TWO_FACTOR_CHALLENGE_KEY, None)
    request.session.pop(SESSION_BOOKKEEPER_ID_KEY, None)
    request.session.pop(SESSION_CLIENT_DETAILS_VERIFIED_UNTIL_KEY, None)
    request.session.pop(SESSION_CLIENT_PROFILE_ACCESS_KEY, None)
    request.session.set_expiry(
        max(
            1,
            int(getattr(settings, "SAFEBOOKS_ADMIN_SESSION_MAX_AGE_SECONDS", 8 * 60 * 60)),
        )
    )
    request.session.modified = True


def _admin_two_factor_failure_cache_key(account_id: int) -> str:
    return f"safebooks:admin-2fa-login-failures:{account_id}"


def _admin_two_factor_login_policy() -> tuple[int, int, int]:
    timeout_seconds = max(
        30,
        int(getattr(settings, "SAFEBOOKS_ADMIN_TWO_FACTOR_LOGIN_TIMEOUT_SECONDS", 300)),
    )
    max_attempts = max(
        1,
        int(getattr(settings, "SAFEBOOKS_ADMIN_TWO_FACTOR_LOGIN_MAX_ATTEMPTS", 5)),
    )
    lockout_seconds = max(
        timeout_seconds,
        int(getattr(settings, "SAFEBOOKS_ADMIN_TWO_FACTOR_LOGIN_LOCKOUT_SECONDS", 300)),
    )
    return timeout_seconds, max_attempts, lockout_seconds


def _set_admin_two_factor_challenge(request, account_id: AdminAccount | int) -> None:
    account = account_id if isinstance(account_id, AdminAccount) else AdminAccount.objects.get(id=account_id)
    account_id = account.id
    timeout_seconds, _max_attempts, _lockout_seconds = _admin_two_factor_login_policy()
    request.session.cycle_key()
    _clear_authentication_state(request)
    request.session.pop(SESSION_BOOKKEEPER_ID_KEY, None)
    request.session.pop(SESSION_CLIENT_DETAILS_VERIFIED_UNTIL_KEY, None)
    request.session.pop(SESSION_CLIENT_PROFILE_ACCESS_KEY, None)
    request.session[SESSION_ADMIN_TWO_FACTOR_CHALLENGE_KEY] = {
        "admin_id": account_id,
        "issued_at": int(timezone.now().timestamp()),
        "attempts": 0,
        "auth_hash": account_session_auth_hash(account),
    }
    request.session.set_expiry(timeout_seconds)
    request.session.modified = True


def _complete_admin_login(request, admin_account: AdminAccount, *, method: str) -> dict:
    admin_account.last_login = timezone.now()
    admin_account.save(update_fields=["last_login"])
    _set_admin_session(request, admin_account, second_factor_verified=method in {"authenticator", "recovery_code"})
    record_admin_auth_event(
        admin_account,
        AdminAuditLog.ACTION_ADMIN_LOGIN,
        authentication_method=method,
    )
    return {
        "ok": True,
        "message": "Login successful.",
        "role": "admin",
        "user": {
            "id": admin_account.id,
            "full_name": admin_account.full_name,
            "email": admin_account.email,
        },
        "redirect_url": reverse("admin_dashboard"),
    }


def _decode_request_data(request):
    content_type = (request.content_type or "").lower()

    if "application/json" not in content_type:
        if request.POST:
            return request.POST.dict()
        return None

    try:
        def reject_nonfinite_constant(_value):
            raise ValueError("Non-finite JSON numbers are not supported.")
        payload = json.loads(request.body.decode("utf-8") or "{}", parse_constant=reject_nonfinite_constant)
    except (ValueError, UnicodeDecodeError, RecursionError):
        return None

    if not isinstance(payload, dict):
        return None

    return payload


def _no_store_json(payload: dict, *, status: int = 200) -> JsonResponse:
    response = JsonResponse(payload, status=status)
    response["Cache-Control"] = "no-store"
    return response


def _is_api_request(request):
    path = request.path or ""
    accepts_header = (request.headers.get("Accept") or "").lower()
    requested_with = request.headers.get("X-Requested-With") or ""

    return (
        path.startswith("/api/")
        or "application/json" in accepts_header
        or requested_with == "XMLHttpRequest"
    )


def _get_session_bookkeeper(request):
    account_id = _session_timestamp(request.session.get(SESSION_BOOKKEEPER_ID_KEY))
    if not account_id:
        return None

    account = BookkeeperAccount.objects.filter(id=account_id).first()
    if (
        account is None
        or not session_auth_hash_matches(account, request.session.get(SESSION_BOOKKEEPER_AUTH_HASH_KEY))
        or (account.two_factor_enabled and not account.two_factor_secret)
    ):
        # Never bootstrap a missing proof from an account ID: it may be an old
        # session that did not complete 2FA or predates a password reset.
        request.session.flush()
        return None
    if not request.session.get_expire_at_browser_close():
        # Upgrade sessions created before the browser-close policy so the
        # existing persistent cookie is replaced on the next response.
        request.session.set_expiry(0)
        request.session.modified = True

    return account


def _get_session_admin(request):
    account_id = _session_timestamp(request.session.get(SESSION_ADMIN_ID_KEY))
    if not account_id:
        return None

    now_timestamp = int(timezone.now().timestamp())
    if _admin_session_is_expired(request, now_timestamp):
        request.session.flush()
        return None

    account = AdminAccount.objects.filter(id=account_id, is_active=True).first()
    if (
        account is None
        or not session_auth_hash_matches(account, request.session.get(SESSION_ADMIN_AUTH_HASH_KEY))
        or (account.two_factor_enabled and not account.two_factor_secret)
    ):
        request.session.flush()
        return None

    # Avoid a session write for every rapid API request while still keeping
    # the idle timer accurate for normal admin activity.
    last_activity_at = _session_timestamp(
        request.session.get(SESSION_ADMIN_LAST_ACTIVITY_AT_KEY)
    )
    if now_timestamp - last_activity_at >= 60:
        request.session[SESSION_ADMIN_LAST_ACTIVITY_AT_KEY] = now_timestamp
        request.session.modified = True

    return account



def _build_user_context(account):
    display_name = (
        (account.full_name or "").strip()
        or (account.username or "").strip()
        or (account.email or "").strip()
        or "Bookkeeper User"
    )

    name_parts = display_name.split()
    if not name_parts:
        initials = "SB"
    elif len(name_parts) == 1:
        initials = name_parts[0][:2].upper()
    else:
        initials = f"{name_parts[0][0]}{name_parts[1][0]}".upper()

    return {
        "current_user_name": display_name,
        "current_user_initials": initials,
    }


def _client_details_lock_enabled(account) -> bool:
    return bool(getattr(account, "client_details_password_required", False))


def _get_client_details_verified_until(request) -> int:
    raw_value = request.session.get(SESSION_CLIENT_DETAILS_VERIFIED_UNTIL_KEY)
    try:
        return int(raw_value or 0)
    except (TypeError, ValueError):
        return 0


def _client_profile_grant_matches(request, client_id=None) -> bool:
    grant = request.session.get(SESSION_CLIENT_PROFILE_ACCESS_KEY)
    if not isinstance(grant, dict):
        return False
    account = request.bookkeeper_account
    return (
        grant.get("bookkeeper_id") == account.id
        and _session_timestamp(grant.get("expires_at")) > int(timezone.now().timestamp())
        and grant.get("password_digest") == sha256(account.password_hash.encode()).hexdigest()
        and (client_id is None or grant.get("client_id") in (None, client_id))
    )


def _is_client_details_access_verified(request, client_id=None) -> bool:
    return (
        _get_client_details_verified_until(request) > int(timezone.now().timestamp())
        and _client_profile_grant_matches(request, client_id)
    )


def _set_client_details_access_verified(request, client_id=None) -> int:
    verified_until = int(timezone.now().timestamp()) + CLIENT_DETAILS_CONFIRMATION_WINDOW_SECONDS
    request.session[SESSION_CLIENT_DETAILS_VERIFIED_UNTIL_KEY] = verified_until
    request.session[SESSION_CLIENT_PROFILE_ACCESS_KEY] = {
        "bookkeeper_id": request.bookkeeper_account.id,
        "client_id": client_id,
        "password_digest": sha256(request.bookkeeper_account.password_hash.encode()).hexdigest(),
        "expires_at": verified_until,
    }
    request.session.modified = True
    return verified_until


def _clear_client_details_access_verified(request, *, clear_profile=True) -> None:
    if SESSION_CLIENT_DETAILS_VERIFIED_UNTIL_KEY in request.session:
        request.session.pop(SESSION_CLIENT_DETAILS_VERIFIED_UNTIL_KEY, None)
        request.session.modified = True
    if clear_profile:
        request.session.pop(SESSION_CLIENT_PROFILE_ACCESS_KEY, None)


def _authorize_client_profile_request(request, client_id: int) -> bool:
    if not _client_details_lock_enabled(request.bookkeeper_account):
        return True
    if _is_client_details_access_verified(request, client_id):
        grant = dict(request.session[SESSION_CLIENT_PROFILE_ACCESS_KEY])
        grant["client_id"] = client_id
        request.session[SESSION_CLIENT_PROFILE_ACCESS_KEY] = grant
        _clear_client_details_access_verified(request, clear_profile=False)
        return True
    grant = request.session.get(SESSION_CLIENT_PROFILE_ACCESS_KEY)
    return (
        _client_profile_grant_matches(request, client_id)
        and isinstance(grant, dict)
        and grant.get("client_id") == client_id
    )


def _get_client_details_access_target(request):
    if request.GET.get("client_access_required") != "1" or not _client_details_lock_enabled(request.bookkeeper_account):
        return None

    target_url = request.GET.get("next", "")
    if not target_url.startswith("/") or "\\" in target_url:
        return None

    try:
        target = urlsplit(target_url)
        match = resolve(target.path)
    except (ValueError, Resolver404):
        return None

    if target.scheme or target.netloc or target.fragment or match.view_name != "client_details":
        return None

    client_id = match.kwargs.get("client_id")
    detail_url = reverse("client_details", args=[client_id])
    if target.path != detail_url:
        return None

    client = Client.objects.filter(id=client_id, bookkeeper=request.bookkeeper_account).values("id", "client_name").first()
    if client is None:
        return None

    return {
        "clientId": client["id"],
        "clientName": client["client_name"],
        "url": f"{detail_url}?{target.query}" if target.query else detail_url,
    }


def _mask_email_address(email: str) -> str:
    normalized = str(email or "").strip()
    if not normalized or "@" not in normalized:
        return normalized

    local_part, domain = normalized.split("@", 1)
    if len(local_part) <= 2:
        masked_local = f"{local_part[:1]}*" if local_part else "*"
    else:
        masked_local = f"{local_part[0]}{'*' * (len(local_part) - 2)}{local_part[-1]}"

    return f"{masked_local}@{domain}"


def _resolve_post_login_redirect(request, payload):
    default_redirect = reverse("dashboard")
    candidate = str(payload.get("next_url", "")).strip()

    if not candidate:
        return default_redirect

    is_safe = url_has_allowed_host_and_scheme(
        url=candidate,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    )

    if not is_safe:
        return default_redirect

    return candidate


def _build_google_callback_uri(request) -> str:
    configured_uri = str(getattr(settings, "SAFEBOOKS_GOOGLE_OAUTH_REDIRECT_URI", "") or "").strip()
    if configured_uri:
        return configured_uri
    return request.build_absolute_uri(reverse("auth_google_callback"))


def _redirect_auth_feedback(route_name: str, message: str, level: str = "error"):
    query_string = urlencode({
        "auth_message": message,
        "auth_level": level,
    })
    return redirect(f"{reverse(route_name)}?{query_string}")


def _build_auth_page_context(request, extra_context: dict | None = None) -> dict:
    challenge = request.session.get(SESSION_BOOKKEEPER_TWO_FACTOR_CHALLENGE_KEY)
    pending_two_factor = False
    if isinstance(challenge, dict):
        issued_at = _session_timestamp(challenge.get("issued_at"))
        timeout, _attempts, _lockout = _bookkeeper_two_factor_login_policy()
        pending_two_factor = 0 < issued_at <= int(timezone.now().timestamp()) < issued_at + timeout
    context = {
        "google_oauth_configured": is_google_oauth_configured(),
        "auth_feedback_message": str(request.GET.get("auth_message") or "").strip(),
        "auth_feedback_level": str(request.GET.get("auth_level") or "info").strip(),
        "pending_bookkeeper_two_factor": pending_two_factor,
    }
    if extra_context:
        context.update(extra_context)
    return context


def _set_bookkeeper_session(request, account_id: BookkeeperAccount | int, *, second_factor_verified=False) -> None:
    account = account_id if isinstance(account_id, BookkeeperAccount) else BookkeeperAccount.objects.get(id=account_id)
    account_id = account.id
    if account.two_factor_enabled and not second_factor_verified:
        raise ValueError("Bookkeeper second-factor verification is required.")
    request.session.cycle_key()
    _clear_authentication_state(request)
    request.session[SESSION_BOOKKEEPER_ID_KEY] = account_id
    request.session[SESSION_BOOKKEEPER_AUTH_HASH_KEY] = account_session_auth_hash(account)
    _clear_admin_session(request)
    request.session.pop(SESSION_CLIENT_DETAILS_VERIFIED_UNTIL_KEY, None)
    request.session.pop(SESSION_CLIENT_PROFILE_ACCESS_KEY, None)
    # Keep authenticated bookkeeper access limited to the current browser
    # session instead of issuing Django's default persistent session cookie.
    request.session.set_expiry(0)
    request.session.modified = True


def _redirect_after_bookkeeper_auth(request, result: dict, next_url: str = ""):
    result = _finish_bookkeeper_primary_auth(request, result, {"next_url": next_url})
    if not result.get("ok"):
        return _redirect_auth_feedback("login", result.get("message", "Unable to complete sign-in."))
    if result.get("requires_two_factor"):
        return redirect("login")
    return redirect(result["redirect_url"])


def _bookkeeper_two_factor_failure_cache_key(account_id: int) -> str:
    return f"safebooks:bookkeeper-2fa-login-failures:{account_id}"


def _bookkeeper_two_factor_login_policy() -> tuple[int, int, int]:
    timeout = max(30, int(getattr(settings, "SAFEBOOKS_BOOKKEEPER_TWO_FACTOR_LOGIN_TIMEOUT_SECONDS", 300)))
    attempts = max(1, int(getattr(settings, "SAFEBOOKS_BOOKKEEPER_TWO_FACTOR_LOGIN_MAX_ATTEMPTS", 5)))
    lockout = max(timeout, int(getattr(settings, "SAFEBOOKS_BOOKKEEPER_TWO_FACTOR_LOGIN_LOCKOUT_SECONDS", 300)))
    return timeout, attempts, lockout


def _increment_two_factor_failures(cache_key: str, timeout: int) -> int:
    if cache.add(cache_key, 1, timeout):
        return 1
    try:
        return cache.incr(cache_key)
    except ValueError:
        # The cache entry may expire between add and incr.
        if cache.add(cache_key, 1, timeout):
            return 1
        return cache.incr(cache_key)


def _finish_bookkeeper_primary_auth(request, result: dict, payload: dict) -> dict:
    authentication_hash = result.pop("_auth_hash", None)
    account_id = (result.get("user") or {}).get("id")
    account = BookkeeperAccount.objects.filter(id=account_id).first()
    if account is None or account.status in {BookkeeperAccount.STATUS_REJECTED, BookkeeperAccount.STATUS_SUSPENDED}:
        return {"ok": False, "message": "Unable to complete sign-in. Account is not active."}
    if not session_auth_hash_matches(account, authentication_hash):
        return {"ok": False, "message": "Security settings changed during sign-in. Sign in again."}
    if account.two_factor_enabled:
        if not account.two_factor_secret:
            _clear_authentication_state(request)
            return {"ok": False, "message": "Authenticator settings are incomplete. Contact support before signing in."}
        timeout, max_attempts, _lockout = _bookkeeper_two_factor_login_policy()
        failures = int(cache.get(_bookkeeper_two_factor_failure_cache_key(account.id), 0) or 0)
        if failures >= max_attempts:
            _clear_authentication_state(request)
            return {"ok": False, "message": "Too many verification attempts. Wait a few minutes before trying again."}
        request.session.cycle_key()
        _clear_authentication_state(request)
        request.session[SESSION_BOOKKEEPER_TWO_FACTOR_CHALLENGE_KEY] = {
            "bookkeeper_id": account.id,
            "issued_at": int(timezone.now().timestamp()),
            "attempts": 0,
            "next_url": _resolve_post_login_redirect(request, payload),
            "auth_hash": account_session_auth_hash(account),
        }
        request.session.set_expiry(timeout)
        return {
            "ok": True, "message": "Sign-in accepted. Enter your 6-digit verification code.",
            "role": "bookkeeper", "requires_two_factor": True,
            "challenge_expires_in_seconds": timeout,
        }
    _set_bookkeeper_session(request, account)
    complete_bookkeeper_login(account)
    if not account.email_verified:
        result["redirect_url"] = reverse("verify_email")
        verification = send_email_verification_code(account, force=False)
        result["verification_email_sent"] = verification.get("ok", False)
        if "retry_after_seconds" in verification:
            result["verification_retry_after_seconds"] = verification["retry_after_seconds"]
    elif account.status == BookkeeperAccount.STATUS_PENDING:
        result["redirect_url"] = reverse("pending_approval")
    else:
        result["redirect_url"] = _resolve_post_login_redirect(request, payload)
    return result


def _build_admin_context(account):
    display_name = (account.full_name or "").strip() or (account.email or "").strip() or "System Admin"

    name_parts = display_name.split()
    if not name_parts:
        initials = "SA"
    elif len(name_parts) == 1:
        initials = name_parts[0][:2].upper()
    else:
        initials = f"{name_parts[0][0]}{name_parts[1][0]}".upper()

    return {
        "current_admin_name": display_name,
        "current_admin_initials": initials,
        "current_admin_email": account.email,
        "current_admin_last_login": account.last_login,
        "current_admin_role_label": "System Manager",
    }


def require_bookkeeper_auth(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        account = _get_session_bookkeeper(request)
        if account is None:
            admin_account = _get_session_admin(request)
            if admin_account is not None:
                if _is_api_request(request):
                    return JsonResponse(
                        {"ok": False, "message": "Bookkeeper access required."},
                        status=403,
                    )

                return redirect("admin_dashboard")

            if _is_api_request(request):
                return JsonResponse(
                    {"ok": False, "message": "Authentication required."},
                    status=401,
                )

            login_url = reverse("login")
            next_path = request.get_full_path()
            if next_path and next_path != login_url:
                query = urlencode({"next": next_path})
                return redirect(f"{login_url}?{query}")

            return redirect(login_url)

        status = account.status or BookkeeperAccount.STATUS_PENDING
        pending_path = reverse("pending_approval")

        if status in {BookkeeperAccount.STATUS_REJECTED, BookkeeperAccount.STATUS_SUSPENDED}:
            request.session.pop(SESSION_BOOKKEEPER_ID_KEY, None)
            request.session.modified = True

            if _is_api_request(request):
                return JsonResponse(
                    {"ok": False, "message": "Account not active."},
                    status=403,
                )

            return redirect("login")

        verify_email_path = reverse("verify_email")
        verify_api_path = reverse("api_verify_email")
        resend_api_path = reverse("api_resend_verification")
        logout_api_path = reverse("api_logout")
        allowed_unverified_paths = {
            verify_email_path,
            verify_api_path,
            resend_api_path,
            logout_api_path,
        }

        if not getattr(account, "email_verified", True):
            if request.path in allowed_unverified_paths:
                request.bookkeeper_account = account
                return view_func(request, *args, **kwargs)

            if _is_api_request(request):
                return JsonResponse(
                    {"ok": False, "message": "Email verification required."},
                    status=403,
                )

            return redirect("verify_email")

        if status == BookkeeperAccount.STATUS_PENDING:
            if request.path == pending_path:
                request.bookkeeper_account = account
                return view_func(request, *args, **kwargs)

            if _is_api_request(request):
                return JsonResponse(
                    {"ok": False, "message": "Approval required."},
                    status=403,
                )

            return redirect("pending_approval")

        if status == BookkeeperAccount.STATUS_APPROVED and request.path == pending_path:
            return redirect("dashboard")

        request.bookkeeper_account = account
        return view_func(request, *args, **kwargs)

    return _wrapped_view


def require_admin_auth(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        account = _get_session_admin(request)
        if account is None:
            bookkeeper_account = _get_session_bookkeeper(request)
            if bookkeeper_account is not None:
                if _is_api_request(request):
                    return JsonResponse(
                        {"ok": False, "message": "Admin access required."},
                        status=403,
                    )

                return redirect("dashboard")

            if _is_api_request(request):
                return JsonResponse(
                    {"ok": False, "message": "Admin authentication required."},
                    status=401,
                )

            login_url = reverse("login")
            next_path = request.get_full_path()
            if next_path and next_path != login_url:
                query = urlencode({"next": next_path})
                return redirect(f"{login_url}?{query}")

            return redirect(login_url)

        request.admin_account = account
        return view_func(request, *args, **kwargs)

    return _wrapped_view


def require_any_auth(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        admin_account = _get_session_admin(request)
        bookkeeper_account = _get_session_bookkeeper(request)

        if admin_account is None and bookkeeper_account is None:
            if _is_api_request(request):
                return JsonResponse(
                    {"ok": False, "message": "Authentication required."},
                    status=401,
                )

            return redirect("login")

        return view_func(request, *args, **kwargs)

    return _wrapped_view


def home_page_view(request):
    if _get_session_admin(request):
        return redirect("admin_dashboard")

    bookkeeper_account = _get_session_bookkeeper(request)
    if bookkeeper_account:
        if not bookkeeper_account.email_verified:
            return redirect("verify_email")
        status = bookkeeper_account.status or BookkeeperAccount.STATUS_PENDING
        if status == BookkeeperAccount.STATUS_PENDING:
            return redirect("pending_approval")
        if status in {BookkeeperAccount.STATUS_REJECTED, BookkeeperAccount.STATUS_SUSPENDED}:
            request.session.pop(SESSION_BOOKKEEPER_ID_KEY, None)
            request.session.modified = True
            return redirect("login")
        return redirect("dashboard")

    return render(request, "authentication/landing.html")


def login_page_view(request):
    if _get_session_admin(request):
        return redirect("admin_dashboard")

    bookkeeper_account = _get_session_bookkeeper(request)
    if bookkeeper_account:
        if not bookkeeper_account.email_verified:
            return redirect("verify_email")
        status = bookkeeper_account.status or BookkeeperAccount.STATUS_PENDING
        if status == BookkeeperAccount.STATUS_PENDING:
            return redirect("pending_approval")
        if status in {BookkeeperAccount.STATUS_REJECTED, BookkeeperAccount.STATUS_SUSPENDED}:
            request.session.pop(SESSION_BOOKKEEPER_ID_KEY, None)
            request.session.modified = True
            return render(request, "authentication/login.html", _build_auth_page_context(request))
        return redirect("dashboard")

    return render(request, "authentication/login.html", _build_auth_page_context(request))


def signup_page_view(request):
    if _get_session_admin(request):
        return redirect("admin_dashboard")

    bookkeeper_account = _get_session_bookkeeper(request)
    if bookkeeper_account:
        if not bookkeeper_account.email_verified:
            return redirect("verify_email")
        status = bookkeeper_account.status or BookkeeperAccount.STATUS_PENDING
        if status == BookkeeperAccount.STATUS_PENDING:
            return redirect("pending_approval")
        if status in {BookkeeperAccount.STATUS_REJECTED, BookkeeperAccount.STATUS_SUSPENDED}:
            request.session.pop(SESSION_BOOKKEEPER_ID_KEY, None)
            request.session.modified = True
            return render(request, "authentication/signup.html", _build_auth_page_context(request))
        return redirect("dashboard")

    google_profile = request.session.get(SESSION_GOOGLE_SIGNUP_PROFILE_KEY)
    context = _build_auth_page_context(request, {
        "google_signup_profile": google_profile if isinstance(google_profile, dict) else None,
    })
    return render(request, "authentication/signup.html", context)


def auth_google_start_view(request):
    if not is_google_oauth_configured():
        return _redirect_auth_feedback(
            "login",
            "Google sign-in is not configured yet. Add the Google OAuth client ID and secret in your environment settings.",
        )

    state = secrets.token_urlsafe(32)
    next_url = str(request.GET.get("next") or "").strip()
    mode = str(request.GET.get("mode") or "login").strip().lower()
    if mode not in {"login", "signup"}:
        mode = "login"

    request.session[SESSION_GOOGLE_OAUTH_STATE_KEY] = {
        "state": state,
        "next_url": next_url,
        "mode": mode,
    }
    request.session.modified = True

    authorization_url = build_google_oauth_authorization_url(
        redirect_uri=_build_google_callback_uri(request),
        state=state,
    )
    return redirect(authorization_url)


def auth_google_callback_view(request):
    error = str(request.GET.get("error") or "").strip()
    if error:
        return _redirect_auth_feedback("login", "Google sign-in was cancelled or denied.")

    state = str(request.GET.get("state") or "").strip()
    stored_state = request.session.get(SESSION_GOOGLE_OAUTH_STATE_KEY)
    if not isinstance(stored_state, dict) or state != stored_state.get("state"):
        request.session.pop(SESSION_GOOGLE_OAUTH_STATE_KEY, None)
        request.session.modified = True
        return _redirect_auth_feedback("login", "Google sign-in session expired. Please try again.")

    code = str(request.GET.get("code") or "").strip()
    token_result = exchange_google_oauth_code(code, _build_google_callback_uri(request))
    request.session.pop(SESSION_GOOGLE_OAUTH_STATE_KEY, None)
    request.session.modified = True

    if not token_result.get("ok"):
        return _redirect_auth_feedback("login", token_result.get("message", "Unable to verify Google sign-in."))

    auth_result = authenticate_google_bookkeeper(token_result.get("profile") or {})
    if not auth_result.get("ok"):
        return _redirect_auth_feedback("login", auth_result.get("message", "Unable to continue with Google."))

    if auth_result.get("requires_signup_completion"):
        profile = token_result.get("profile") or {}
        request.session[SESSION_GOOGLE_SIGNUP_PROFILE_KEY] = {
            "google_sub": profile.get("google_sub"),
            "email": profile.get("email"),
            "full_name": profile.get("full_name"),
        }
        request.session.modified = True
        return redirect(f"{reverse('signup')}?google_setup=1")

    return _redirect_after_bookkeeper_auth(
        request,
        auth_result,
        next_url=str(stored_state.get("next_url") or ""),
    )


@require_bookkeeper_auth
@ensure_csrf_cookie
def dashboard_page_view(request):
    context = _build_user_context(request.bookkeeper_account)
    context["active_nav"] = "dashboard"
    return render(request, "base/dashboard.html", context)


@require_bookkeeper_auth
@ensure_csrf_cookie
def clients_page_view(request):
    _clear_client_details_access_verified(request)
    context = _build_user_context(request.bookkeeper_account)
    context["active_nav"] = "clients"
    context["client_details_password_required"] = _client_details_lock_enabled(request.bookkeeper_account)
    context["client_details_access_verified"] = False
    context["client_details_verified_until"] = 0
    context["client_details_access_target"] = _get_client_details_access_target(request)
    return render(request, "base/clients.html", context)


@require_bookkeeper_auth
@ensure_csrf_cookie
def financial_records_page_view(request):
    context = _build_user_context(request.bookkeeper_account)
    context["active_nav"] = "financial_records"
    return render(request, "base/financial_records.html", context)


@require_bookkeeper_auth
@ensure_csrf_cookie
def financial_records_client_page_view(request):
    context = _build_user_context(request.bookkeeper_account)
    context["active_nav"] = "financial_records"
    return render(request, "base/financial_records_client.html", context)


@require_bookkeeper_auth
@ensure_csrf_cookie
def client_details_page_view(request, client_id):
    from django.shortcuts import get_object_or_404
    from safebooks.models import Client
    client = get_object_or_404(Client, id=client_id, bookkeeper=request.bookkeeper_account)
    if _client_details_lock_enabled(request.bookkeeper_account) and not _is_client_details_access_verified(request, client_id):
        query = urlencode({
            "client_access_required": "1",
            "next": request.get_full_path(),
        })
        return redirect(f"{reverse('clients')}?{query}")

    if _client_details_lock_enabled(request.bookkeeper_account):
        _authorize_client_profile_request(request, client_id)
    else:
        _clear_client_details_access_verified(request)

    context = _build_user_context(request.bookkeeper_account)
    context["active_nav"] = "clients"
    client.remarks = resolve_client_remarks(client)
    context["client"] = client
    context["client_record_email_notifications_enabled"] = bool(
        getattr(request.bookkeeper_account, "client_record_email_notifications_enabled", True)
    )
    response = render(request, "base/client_details.html", context)
    response["Cache-Control"] = "no-store"
    return response


@require_bookkeeper_auth
@ensure_csrf_cookie
def reports_page_view(request):
    query = urlencode({
        "report_scope": "client",
    })
    return redirect(f"{reverse('clients')}?{query}")


@require_bookkeeper_auth
@ensure_csrf_cookie
def pending_approval_page_view(request):
    context = _build_user_context(request.bookkeeper_account)
    context["active_nav"] = ""
    return render(request, "authentication/pending_approval.html", context)


@require_bookkeeper_auth
@ensure_csrf_cookie
def verify_email_page_view(request):
    account = request.bookkeeper_account
    if getattr(account, "email_verified", True):
        status = account.status or BookkeeperAccount.STATUS_PENDING
        if status == BookkeeperAccount.STATUS_PENDING:
            return redirect("pending_approval")
        if status == BookkeeperAccount.STATUS_APPROVED:
            return redirect("dashboard")

    context = _build_user_context(account)
    context["active_nav"] = ""
    context["verification_email"] = account.email
    context["verification_email_masked"] = _mask_email_address(account.email)
    context["verification_resend_cooldown_seconds"] = getattr(
        settings,
        "SAFEBOOKS_EMAIL_VERIFICATION_RESEND_COOLDOWN_SECONDS",
        60,
    )
    email_backend = getattr(settings, "EMAIL_BACKEND", "")
    if settings.DEBUG and email_backend == "django.core.mail.backends.console.EmailBackend":
        context["verification_delivery_hint"] = (
            "Dev note: verification emails are printed in the server console."
        )
    return render(request, "authentication/email_verification.html", context)


@require_bookkeeper_auth
@ensure_csrf_cookie
def settings_page_view(request):
    context = _build_user_context(request.bookkeeper_account)
    context["active_nav"] = "settings"
    context["login_alerts_enabled"] = bool(getattr(request.bookkeeper_account, "login_alerts_enabled", False))
    context["client_record_email_notifications_enabled"] = bool(
        getattr(request.bookkeeper_account, "client_record_email_notifications_enabled", True)
    )
    context["client_details_password_required"] = _client_details_lock_enabled(request.bookkeeper_account)
    context["login_alerts_destination"] = _mask_email_address(request.bookkeeper_account.email)
    context["email_delivery_hint"] = email_delivery_hint()
    context["client_record_email_service_enabled"] = bool(settings.SAFEBOOKS_CLIENT_RECORD_EMAILS_ENABLED)
    context["deactivation_request_pending"] = bool(
        get_deactivation_request_status(request.bookkeeper_account).get("pending_request")
    )
    context["two_factor_enabled"] = bool(
        request.bookkeeper_account.two_factor_enabled and request.bookkeeper_account.two_factor_secret
    )
    return render(request, "base/settings.html", context)


@require_bookkeeper_auth
@ensure_csrf_cookie
def profile_page_view(request):
    context = _build_user_context(request.bookkeeper_account)
    context["active_nav"] = "profile"
    context["profile_data"] = {
        "full_name": request.bookkeeper_account.full_name or "",
        "username": request.bookkeeper_account.username or "",
        "email": request.bookkeeper_account.email or "",
        "location": getattr(request.bookkeeper_account, "location", "") or "",
    }
    return render(request, "base/profile.html", context)


@require_bookkeeper_auth
@ensure_csrf_cookie
def bookkeeper_audit_log_page_view(request):
    context = _build_user_context(request.bookkeeper_account)
    context["active_nav"] = "audit_log"
    return render(request, "base/audit_log.html", context)


@require_admin_auth
@ensure_csrf_cookie
def admin_dashboard_page_view(request):
    context = _build_admin_context(request.admin_account)
    context["active_admin_nav"] = "dashboard"
    return render(request, "admin_panel/dashboard.html", context)


@require_admin_auth
@ensure_csrf_cookie
def admin_bookkeepers_page_view(request):
    context = _build_admin_context(request.admin_account)
    context["active_admin_nav"] = "bookkeepers"
    return render(request, "admin_panel/bookkeepers.html", context)


@require_admin_auth
@ensure_csrf_cookie
def admin_approvals_page_view(request):
    context = _build_admin_context(request.admin_account)
    context["active_admin_nav"] = "approvals"
    return render(request, "admin_panel/approvals.html", context)


@require_admin_auth
@ensure_csrf_cookie
def admin_audit_log_page_view(request):
    context = _build_admin_context(request.admin_account)
    context["active_admin_nav"] = "audit_log"
    return render(request, "admin_panel/audit_log.html", context)


@require_admin_auth
@ensure_csrf_cookie
def admin_system_settings_page_view(request):
    context = _build_admin_context(request.admin_account)
    context["active_admin_nav"] = "system_settings"
    return render(request, "admin_panel/system_settings.html", context)


@require_admin_auth
@ensure_csrf_cookie
def admin_profile_page_view(request):
    context = _build_admin_context(request.admin_account)
    context["active_admin_nav"] = "profile"
    return render(request, "admin_panel/admin_profile.html", context)


def _resolve_client_error_status(result):
    message = result.get("message", "")
    if message == "Client not found.":
        return 404
    if message == "TIN already exists.":
        return 409
    return 400


def _resolve_financial_record_error_status(result):
    if result.get("code") in {"stale_record", "revision_required", "write_conflict"}:
        return 409
    if result.get("code") == "persistence_failed":
        return 503
    message = result.get("message", "")
    if message in {"Client not found.", "Financial record not found."}:
        return 404
    return 400


def _resolve_analytics_error_status(result):
    message = result.get("message", "")
    if message == "Client not found.":
        return 404
    return 400


def _resolve_admin_approval_error_status(result):
    if result.get("code") == "stale_decision":
        return 409
    message = result.get("message", "")
    if message == "Bookkeeper not found.":
        return 404
    return 400


def _resolve_admin_bookkeeper_error_status(result):
    if result.get("code") == "stale_decision":
        return 409
    message = result.get("message", "")
    if message == "Bookkeeper not found.":
        return 404
    return 400


@require_http_methods(["GET", "POST"])
@require_bookkeeper_auth
def workspace_defaults_api_view(request):
    if request.method == "GET":
        result = get_workspace_defaults_for_bookkeeper(request.bookkeeper_account)
        return JsonResponse(result)

    payload = _decode_request_data(request)
    if payload is None:
        return JsonResponse(
            {"ok": False, "message": "Invalid request payload."},
            status=400,
        )

    result = update_workspace_defaults_for_bookkeeper(request.bookkeeper_account, payload)
    if result.get("ok"):
        return JsonResponse(result)

    return JsonResponse(result, status=400)


@require_POST
@require_bookkeeper_auth
def security_change_password_api_view(request):
    payload = _decode_request_data(request)
    if payload is None:
        return JsonResponse(
            {"ok": False, "message": "Invalid request payload."},
            status=400,
        )

    result = change_bookkeeper_password(request.bookkeeper_account, payload)
    if result.get("ok"):
        _renew_current_authenticated_session(request, request.bookkeeper_account)
        record_bookkeeper_audit(
            request.bookkeeper_account,
            BookkeeperAuditLog.ACTION_PASSWORD_CHANGED,
            "Changed account password.",
            target_model="BookkeeperAccount",
            target_id=request.bookkeeper_account.id,
        )
        return JsonResponse(result)

    return JsonResponse(result, status=400)


@require_POST
@require_bookkeeper_auth
def security_login_alerts_api_view(request):
    payload = _decode_request_data(request)
    if payload is None:
        return JsonResponse(
            {"ok": False, "message": "Invalid request payload."},
            status=400,
        )

    return _update_audited_preference(request, payload, update_login_alerts_preference,
        "login_alerts_enabled", BookkeeperAuditLog.ACTION_LOGIN_ALERTS_CHANGED, "login alerts")


def _update_audited_preference(request, payload, update, field, action, label, *, after_success=None):
    account = request.bookkeeper_account
    previous = getattr(account, field)
    try:
        with transaction.atomic():
            result = update(account, payload)
            if result.get("ok"):
                enabled = bool(result.get(field))
                record_bookkeeper_audit(account, action, f"Turned {label} {'on' if enabled else 'off'}.",
                    target_model="BookkeeperAccount", target_id=account.id, metadata={"enabled": enabled})
    except DatabaseError as error:
        setattr(account, field, previous)
        logger.warning("Preference update could not be confirmed (%s).", type(error).__name__)
        return _no_store_json({"ok": False, "message": "Update could not be confirmed. Reload Settings before retrying."}, status=503)
    if result.get("ok") and after_success is not None:
        after_success(result)
    return JsonResponse(result, status=200 if result.get("ok") else 400)


@require_POST
@require_bookkeeper_auth
def settings_client_record_email_notifications_api_view(request):
    payload = _decode_request_data(request)
    if payload is None:
        return JsonResponse(
            {"ok": False, "message": "Invalid request payload."},
            status=400,
        )

    return _update_audited_preference(request, payload, update_client_record_email_notifications_preference,
        "client_record_email_notifications_enabled", BookkeeperAuditLog.ACTION_CLIENT_EMAILS_CHANGED, "client record emails")


@require_POST
@require_bookkeeper_auth
def security_client_details_access_confirm_api_view(request):
    payload = _decode_request_data(request)
    if payload is None:
        return JsonResponse(
            {"ok": False, "message": "Invalid request payload."},
            status=400,
        )

    client_id = payload.get("client_id")
    if client_id is not None:
        if isinstance(client_id, bool) or not str(client_id).isdigit():
            return _no_store_json({"ok": False, "message": "Invalid client id."}, status=400)
        client_id = int(client_id)
        if not Client.objects.filter(id=client_id, bookkeeper=request.bookkeeper_account).exists():
            return _no_store_json({"ok": False, "message": "Client not found."}, status=404)

    result = confirm_client_details_access(request.bookkeeper_account, payload)
    if result.get("ok"):
        verified_until = _set_client_details_access_verified(request, client_id)
        result["verified_until"] = verified_until
        result["verified_for_seconds"] = CLIENT_DETAILS_CONFIRMATION_WINDOW_SECONDS
        return _no_store_json(result)

    return _no_store_json(result, status=400)


@require_POST
@require_bookkeeper_auth
def security_client_details_access_preference_api_view(request):
    payload = _decode_request_data(request)
    if payload is None:
        return JsonResponse(
            {"ok": False, "message": "Invalid request payload."},
            status=400,
        )

    def clear_disabled_grant(result):
        if not result["client_details_password_required"]:
            _clear_client_details_access_verified(request)
    return _update_audited_preference(request, payload, update_client_details_access_preference,
        "client_details_password_required", BookkeeperAuditLog.ACTION_CLIENT_DETAILS_LOCK_CHANGED,
        "client details lock", after_success=clear_disabled_grant)


@require_POST
@require_bookkeeper_auth
def bookkeeper_two_factor_setup_api_view(request):
    result = create_bookkeeper_two_factor_setup(request.bookkeeper_account)
    if result.get("ok"):
        request.session[SESSION_BOOKKEEPER_TWO_FACTOR_SETUP_KEY] = {
            "bookkeeper_id": request.bookkeeper_account.id,
            "secret": result.get("secret", ""),
            "issued_at": int(timezone.now().timestamp()),
        }
        request.session.modified = True
    response = JsonResponse(result, status=200 if result.get("ok") else 400)
    if result.get("ok"):
        response["Cache-Control"] = "no-store"
    return response


@require_POST
@require_bookkeeper_auth
def bookkeeper_two_factor_confirm_api_view(request):
    payload = _decode_request_data(request)
    if payload is None:
        return JsonResponse(
            {"ok": False, "message": "Invalid request payload."},
            status=400,
        )

    setup_state = request.session.get(SESSION_BOOKKEEPER_TWO_FACTOR_SETUP_KEY)
    if not isinstance(setup_state, dict):
        return JsonResponse({
            "ok": False,
            "message": "Authenticator setup expired. Please start setup again.",
        }, status=400)

    issued_at = _session_timestamp(setup_state.get("issued_at"))
    timeout_seconds = 5 * 60
    setup_matches_bookkeeper = setup_state.get("bookkeeper_id") == request.bookkeeper_account.id
    setup_is_current = (
        issued_at > 0
        and int(timezone.now().timestamp()) - issued_at < timeout_seconds
    )
    if not setup_matches_bookkeeper or not setup_is_current:
        request.session.pop(SESSION_BOOKKEEPER_TWO_FACTOR_SETUP_KEY, None)
        request.session.modified = True
        return JsonResponse({
            "ok": False,
            "message": "Authenticator setup expired. Please start setup again.",
        }, status=400)

    result = enable_bookkeeper_two_factor(
        request.bookkeeper_account,
        str(setup_state.get("secret") or ""),
        payload,
    )
    if result.get("ok"):
        _renew_current_authenticated_session(request, request.bookkeeper_account)
        request.session.pop(SESSION_BOOKKEEPER_TWO_FACTOR_SETUP_KEY, None)
        request.session.modified = True
        record_bookkeeper_audit(
            request.bookkeeper_account,
            BookkeeperAuditLog.ACTION_TWO_FACTOR_ENABLED,
            "Enabled authenticator two-factor authentication.",
            target_model="BookkeeperAccount",
            target_id=request.bookkeeper_account.id,
        )
    response = JsonResponse(result, status=200 if result.get("ok") else 400)
    if result.get("ok"):
        response["Cache-Control"] = "no-store"
    return response


@require_POST
@require_bookkeeper_auth
def bookkeeper_two_factor_disable_api_view(request):
    payload = _decode_request_data(request)
    if payload is None:
        return JsonResponse(
            {"ok": False, "message": "Invalid request payload."},
            status=400,
        )

    result = disable_bookkeeper_two_factor(request.bookkeeper_account, payload)
    if result.get("ok"):
        _renew_current_authenticated_session(request, request.bookkeeper_account)
        request.session.pop(SESSION_BOOKKEEPER_TWO_FACTOR_SETUP_KEY, None)
        request.session.modified = True
        record_bookkeeper_audit(
            request.bookkeeper_account,
            BookkeeperAuditLog.ACTION_TWO_FACTOR_DISABLED,
            "Disabled authenticator two-factor authentication.",
            target_model="BookkeeperAccount",
            target_id=request.bookkeeper_account.id,
        )
        return JsonResponse(result)

    return JsonResponse(result, status=400)


@require_http_methods(["GET", "POST"])
@require_bookkeeper_auth
def settings_deactivation_request_api_view(request):
    if request.method == "GET":
        result = get_deactivation_request_status(request.bookkeeper_account)
        return JsonResponse(result)

    payload = _decode_request_data(request)
    if payload is None:
        return JsonResponse(
            {"ok": False, "message": "Invalid request payload."},
            status=400,
        )

    result = request_bookkeeper_deactivation(request.bookkeeper_account, payload)
    if result.get("ok"):
        return JsonResponse(result, status=201)

    return JsonResponse(result, status=400)


@require_http_methods(["GET", "POST"])
@require_bookkeeper_auth
def profile_api_view(request):
    if request.method == "GET":
        result = get_profile_for_bookkeeper(request.bookkeeper_account)
        return JsonResponse(result)

    payload = _decode_request_data(request)
    if payload is None:
        return JsonResponse(
            {"ok": False, "message": "Invalid request payload."},
            status=400,
        )

    result = update_profile_for_bookkeeper(request.bookkeeper_account, payload)
    if result.get("ok"):
        record_bookkeeper_audit(
            request.bookkeeper_account,
            BookkeeperAuditLog.ACTION_PROFILE_UPDATED,
            "Updated personal profile details.",
            target_model="BookkeeperAccount",
            target_id=request.bookkeeper_account.id,
            metadata={"email_verification_required": bool(result.get("requires_email_verification"))},
        )
        return JsonResponse(result)

    return JsonResponse(result, status=400)



@require_http_methods(["GET", "POST"])
@require_bookkeeper_auth
def clients_api_view(request):
    if request.method == "GET":
        result = list_clients_for_bookkeeper(request.bookkeeper_account)
        return _no_store_json(result)

    payload = _decode_request_data(request)
    if payload is None:
        return JsonResponse(
            {"ok": False, "message": "Invalid request payload."},
            status=400,
        )

    result = create_client_for_bookkeeper(request.bookkeeper_account, payload)
    if result.get("ok"):
        client_payload = result.get("client") or {}
        client_name = str(client_payload.get("client_name") or "Client")
        record_bookkeeper_audit(
            request.bookkeeper_account,
            BookkeeperAuditLog.ACTION_CLIENT_CREATED,
            f"Added client {client_name}.",
            target_model="Client",
            target_id=client_payload.get("id"),
            metadata={"client_name": client_name},
        )
        return _no_store_json(result, status=201)

    return JsonResponse(result, status=_resolve_client_error_status(result))


@require_http_methods(["GET", "PUT", "PATCH", "DELETE"])
@require_bookkeeper_auth
def client_detail_api_view(request, client_id):
    if not Client.objects.filter(id=client_id, bookkeeper=request.bookkeeper_account).exists():
        return _no_store_json({"ok": False, "message": "Client not found.", "errors": ["Client not found."]}, status=404)
    if request.method != "DELETE" and not _authorize_client_profile_request(request, client_id):
        return _no_store_json({
            "ok": False,
            "message": "Confirm your password in Clients before viewing or editing this client's details.",
            "client_access_required": True,
        }, status=403)
    if request.method == "GET":
        result = get_client_for_bookkeeper(request.bookkeeper_account, client_id)
        return _no_store_json(result, status=200 if result.get("ok") else _resolve_client_error_status(result))

    if request.method == "DELETE":
        payload = _decode_request_data(request)
        if request.body and payload is None:
            return JsonResponse({"ok": False, "message": "Invalid request payload."}, status=400)
        payload = payload or {}
        reason = payload.get("reason") or payload.get("closure_reason") or request.GET.get("reason") or "Closed by bookkeeper"
        notes = payload.get("notes") or payload.get("closure_notes") or ""
        result = delete_client_for_bookkeeper(request.bookkeeper_account, client_id, reason=reason, notes=notes)
        if result.get("ok"):
            client_payload = result.get("client") or {}
            client_name = str(client_payload.get("client_name") or "Client")
            record_bookkeeper_audit(
                request.bookkeeper_account,
                BookkeeperAuditLog.ACTION_CLIENT_CLOSED,
                f"Closed client {client_name}. Reason: {reason}",
                target_model="Client",
                target_id=client_id,
                metadata={"client_name": client_name, "closure_reason": reason, "closure_notes": notes},
            )
            return _no_store_json(result)
        return JsonResponse(result, status=_resolve_client_error_status(result))

    payload = _decode_request_data(request)
    if payload is None:
        return JsonResponse(
            {"ok": False, "message": "Invalid request payload."},
            status=400,
        )

    result = update_client_for_bookkeeper(request.bookkeeper_account, client_id, payload, include_sensitive=True)
    if result.get("ok"):
        client_payload = result.get("client") or {}
        client_name = str(client_payload.get("client_name") or "Client")
        record_bookkeeper_audit(
            request.bookkeeper_account,
            BookkeeperAuditLog.ACTION_CLIENT_UPDATED,
            f"Updated client {client_name}.",
            target_model="Client",
            target_id=client_id,
            metadata={"client_name": client_name},
        )
        return _no_store_json(result)

    return JsonResponse(result, status=_resolve_client_error_status(result))


@require_http_methods(["POST"])
@require_bookkeeper_auth
def client_reopen_api_view(request, client_id):
    result = reopen_client_for_bookkeeper(request.bookkeeper_account, client_id)
    if result.get("ok"):
        client_payload = result.get("client") or {}
        client_name = str(client_payload.get("client_name") or "Client")
        record_bookkeeper_audit(
            request.bookkeeper_account,
            BookkeeperAuditLog.ACTION_CLIENT_UPDATED,
            f"Reopened client {client_name}.",
            target_model="Client",
            target_id=client_id,
            metadata={"client_name": client_name, "action": "reopen"},
        )
        return JsonResponse(result)

    return JsonResponse(result, status=_resolve_client_error_status(result))


@require_http_methods(["GET"])
@require_bookkeeper_auth
def financial_record_clients_api_view(request):
    result = list_financial_clients_for_bookkeeper(request.bookkeeper_account)
    return JsonResponse(result)


@require_http_methods(["GET"])
@require_bookkeeper_auth
def dashboard_summary_api_view(request):
    result = get_dashboard_summary_for_bookkeeper(request.bookkeeper_account)
    return JsonResponse(result)


@require_http_methods(["GET"])
@require_bookkeeper_auth
def analytics_summary_api_view(request):
    client_id_param = (request.GET.get("client_id") or "").strip()
    client_id = None

    if client_id_param:
        if not client_id_param.isascii() or not client_id_param.isdigit() or len(client_id_param) > 18:
            return JsonResponse(
                {"ok": False, "message": "Invalid client id."},
                status=400,
            )
        client_id = int(client_id_param)

    year_param = (request.GET.get("year") or "").strip()
    if year_param and year_param != "all" and (not year_param.isascii() or not year_param.isdigit() or len(year_param) > 4):
        return JsonResponse({"ok": False, "message": "Invalid analytics year."}, status=400)
    year_filter = year_param if year_param.isdigit() else None
    
    horizon_param = (request.GET.get("horizon") or "").strip()
    horizon = horizon_param or 3

    try:
        result = get_analytics_summary_for_bookkeeper(
            request.bookkeeper_account,
            client_id=client_id,
            year_filter=year_filter,
            horizon=horizon,
        )
    except DatabaseError as error:
        logger.warning("Analytics read could not be completed (%s).", type(error).__name__)
        return _no_store_json({
            "ok": False, "code": "analytics_unavailable",
            "message": "Analytics could not be loaded right now. Please retry or select a narrower client/year range.",
        }, status=503)
    if result.get("ok"):
        return JsonResponse(result)

    return JsonResponse(result, status=_resolve_analytics_error_status(result))


@require_http_methods(["GET"])
@require_admin_auth
def admin_approvals_api_view(request):
    status_value = (request.GET.get("status") or "").strip()
    search_value = (request.GET.get("search") or "").strip()
    sort_value = (request.GET.get("sort") or "").strip()
    page_value = (request.GET.get("page") or "").strip()
    page_size_value = (request.GET.get("page_size") or "").strip()

    result = list_admin_approvals(
        request.admin_account,
        status_value,
        search_value,
        sort_value,
        page=page_value,
        page_size=page_size_value,
    )
    return JsonResponse(result)


@require_http_methods(["POST"])
@require_admin_auth
def admin_approvals_approve_api_view(request, bookkeeper_id):
    result = approve_bookkeeper(request.admin_account, bookkeeper_id)
    if result.get("ok"):
        return JsonResponse(result)

    return JsonResponse(result, status=_resolve_admin_approval_error_status(result))


@require_http_methods(["POST"])
@require_admin_auth
def admin_approvals_reject_api_view(request, bookkeeper_id):
    payload = _decode_request_data(request) or {}
    rejection_reason = payload.get("rejection_reason") or payload.get("reason")

    result = reject_bookkeeper(request.admin_account, bookkeeper_id, rejection_reason)
    if result.get("ok"):
        return JsonResponse(result)

    if result.get("message") == "Rejection reason is required.":
        return JsonResponse(result)

    return JsonResponse(result, status=_resolve_admin_approval_error_status(result))


@require_http_methods(["POST"])
@require_admin_auth
def admin_approvals_retry_email_api_view(request, bookkeeper_id):
    result = retry_approval_decision_email(request.admin_account, bookkeeper_id)
    if result.get("ok"):
        return JsonResponse(result)
    return JsonResponse(result, status=_resolve_admin_approval_error_status(result))


@require_http_methods(["GET"])
@require_admin_auth
def admin_bookkeepers_api_view(request):
    status_value = (request.GET.get("status") or "").strip()
    search_value = (request.GET.get("search") or "").strip()
    sort_value = (request.GET.get("sort") or "").strip()
    clients_value = (request.GET.get("clients") or "").strip()
    page_value = (request.GET.get("page") or "").strip()
    page_size_value = (request.GET.get("page_size") or "").strip()

    result = list_admin_bookkeepers(
        request.admin_account,
        status_value,
        search_value,
        sort_value,
        clients_value,
        page_value,
        page_size_value,
    )
    return JsonResponse(result)


@require_http_methods(["POST"])
@require_admin_auth
def admin_bookkeepers_deactivate_api_view(request, bookkeeper_id):
    payload = _decode_request_data(request) or {}
    admin_password = payload.get("admin_password") or payload.get("password")
    request_id_raw = payload.get("deactivation_request_id") or payload.get("request_id")
    request_id = None
    if request_id_raw not in (None, ""):
        try:
            request_id = int(request_id_raw)
        except (TypeError, ValueError):
            return JsonResponse({"ok": False, "message": "Invalid deactivation request id."}, status=400)

    result = deactivate_bookkeeper(request.admin_account, bookkeeper_id, admin_password, request_id=request_id)
    if result.get("ok"):
        return JsonResponse(result)

    if result.get("message") in {"Admin password is required.", "Admin password is incorrect."}:
        return JsonResponse(result)

    return JsonResponse(result, status=_resolve_admin_bookkeeper_error_status(result))


@require_http_methods(["POST"])
@require_admin_auth
def admin_bookkeepers_deactivation_request_decline_api_view(request, request_id):
    payload = _decode_request_data(request) or {}
    admin_password = payload.get("admin_password") or payload.get("password")
    admin_note = payload.get("admin_note") or payload.get("note")
    result = decline_deactivation_request(request.admin_account, request_id, admin_password, admin_note)
    if result.get("ok"):
        return JsonResponse(result)

    if result.get("message") in {"Admin password is required.", "Admin password is incorrect."}:
        return JsonResponse(result)

    return JsonResponse(result, status=_resolve_admin_bookkeeper_error_status(result))


@require_http_methods(["POST"])
@require_admin_auth
def admin_bookkeepers_reactivate_api_view(request, bookkeeper_id):
    payload = _decode_request_data(request) or {}
    admin_password = payload.get("admin_password") or payload.get("password")
    result = reactivate_bookkeeper(request.admin_account, bookkeeper_id, admin_password)
    if result.get("ok"):
        return JsonResponse(result)

    if result.get("message") in {"Admin password is required.", "Admin password is incorrect."}:
        return JsonResponse(result)

    return JsonResponse(result, status=_resolve_admin_bookkeeper_error_status(result))


@require_http_methods(["POST"])
@require_admin_auth
def admin_bookkeepers_delete_api_view(request, bookkeeper_id):
    payload = _decode_request_data(request) or {}
    admin_password = payload.get("admin_password") or payload.get("password")
    result = delete_bookkeeper_account(request.admin_account, bookkeeper_id, admin_password)
    if result.get("ok"):
        return JsonResponse(result)

    if result.get("message") in {"Admin password is required.", "Admin password is incorrect."}:
        return JsonResponse(result)

    return JsonResponse(result, status=_resolve_admin_bookkeeper_error_status(result))


@require_http_methods(["GET"])
@require_admin_auth
def admin_dashboard_summary_api_view(request):
    load_page = (request.GET.get("load_page") or request.GET.get("page") or "").strip()
    load_page_size = (request.GET.get("load_page_size") or request.GET.get("page_size") or "").strip()
    result = get_admin_dashboard_summary(
        request.admin_account,
        load_page=load_page or 1,
        load_page_size=load_page_size or 5,
    )
    return JsonResponse(result)


@require_http_methods(["GET", "POST"])
@require_admin_auth
def admin_profile_api_view(request):
    if request.method == "GET":
        result = get_admin_profile(request.admin_account)
        return JsonResponse(result)

    payload = _decode_request_data(request)
    if payload is None:
        return JsonResponse(
            {"ok": False, "message": "Invalid request payload."},
            status=400,
        )

    result = update_admin_profile(request.admin_account, payload)
    return JsonResponse(result)


@require_http_methods(["POST"])
@require_admin_auth
def admin_security_change_password_api_view(request):
    payload = _decode_request_data(request)
    if payload is None:
        return JsonResponse(
            {"ok": False, "message": "Invalid request payload."},
            status=400,
        )

    result = change_admin_password(request.admin_account, payload)
    if result.get("ok"):
        _renew_current_authenticated_session(request, request.admin_account, admin=True)
    return JsonResponse(result)


@require_http_methods(["POST"])
@require_admin_auth
def admin_two_factor_setup_api_view(request):
    payload = _decode_request_data(request)
    if payload is None:
        return JsonResponse(
            {"ok": False, "message": "Invalid request payload."},
            status=400,
        )

    result = create_admin_two_factor_setup(request.admin_account, payload)
    if result.get("ok"):
        request.session[SESSION_ADMIN_TWO_FACTOR_SETUP_KEY] = {
            "admin_id": request.admin_account.id,
            "secret": result.get("secret", ""),
            "issued_at": int(timezone.now().timestamp()),
        }
        request.session.modified = True
    response = JsonResponse(result)
    if result.get("ok"):
        response["Cache-Control"] = "no-store"
    return response


@require_http_methods(["POST"])
@require_admin_auth
def admin_two_factor_confirm_api_view(request):
    payload = _decode_request_data(request)
    if payload is None:
        return JsonResponse(
            {"ok": False, "message": "Invalid request payload."},
            status=400,
        )

    setup_state = request.session.get(SESSION_ADMIN_TWO_FACTOR_SETUP_KEY)
    if not isinstance(setup_state, dict):
        return JsonResponse({
            "ok": False,
            "message": "Authenticator setup expired. Start setup again.",
        })

    issued_at = _session_timestamp(setup_state.get("issued_at"))
    timeout_seconds = max(
        1,
        int(getattr(settings, "SAFEBOOKS_ADMIN_TWO_FACTOR_PENDING_TIMEOUT_SECONDS", 5 * 60)),
    )
    setup_matches_admin = setup_state.get("admin_id") == request.admin_account.id
    setup_is_current = (
        issued_at > 0
        and int(timezone.now().timestamp()) - issued_at < timeout_seconds
    )
    if not setup_matches_admin or not setup_is_current:
        request.session.pop(SESSION_ADMIN_TWO_FACTOR_SETUP_KEY, None)
        request.session.modified = True
        return JsonResponse({
            "ok": False,
            "message": "Authenticator setup expired. Start setup again.",
        })

    result = enable_admin_two_factor(
        request.admin_account,
        str(setup_state.get("secret") or ""),
        payload,
    )
    if result.get("ok"):
        _renew_current_authenticated_session(request, request.admin_account, admin=True)
        request.session.pop(SESSION_ADMIN_TWO_FACTOR_SETUP_KEY, None)
        request.session.modified = True
    response = JsonResponse(result)
    if result.get("ok"):
        response["Cache-Control"] = "no-store"
    return response


@require_http_methods(["POST"])
@require_admin_auth
def admin_two_factor_disable_api_view(request):
    payload = _decode_request_data(request)
    if payload is None:
        return JsonResponse(
            {"ok": False, "message": "Invalid request payload."},
            status=400,
        )

    result = disable_admin_two_factor(request.admin_account, payload)
    if result.get("ok"):
        _renew_current_authenticated_session(request, request.admin_account, admin=True)
        request.session.pop(SESSION_ADMIN_TWO_FACTOR_SETUP_KEY, None)
        request.session.modified = True
    return JsonResponse(result)


@require_http_methods(["POST"])
@require_admin_auth
def admin_two_factor_recovery_codes_api_view(request):
    payload = _decode_request_data(request)
    if payload is None:
        return JsonResponse(
            {"ok": False, "message": "Invalid request payload."},
            status=400,
        )

    result = regenerate_admin_two_factor_recovery_codes(request.admin_account, payload)
    if result.get("ok"):
        _renew_current_authenticated_session(request, request.admin_account, admin=True)
    response = JsonResponse(result)
    if result.get("ok"):
        response["Cache-Control"] = "no-store"
    return response


@require_http_methods(["GET"])
@require_admin_auth
def admin_audit_log_api_view(request):
    action_value = (request.GET.get("action") or "").strip()
    search_value = (request.GET.get("search") or "").strip()
    sort_value = (request.GET.get("sort") or "").strip()
    date_from_value = (request.GET.get("date_from") or "").strip()
    date_to_value = (request.GET.get("date_to") or "").strip()
    page_value = (request.GET.get("page") or "").strip()
    page_size_value = (request.GET.get("page_size") or "").strip()

    result = list_admin_audit_logs(
        request.admin_account,
        action_value,
        search_value,
        sort_value,
        date_from_value,
        date_to_value,
        page_value,
        page_size_value,
    )
    return JsonResponse(result, status=200 if result.get("ok") else 400)


@require_http_methods(["GET"])
@require_bookkeeper_auth
def reports_print_layout_api_view(request):
    client_id_param = (request.GET.get("client_id") or "").strip()
    if not client_id_param:
        return JsonResponse(
            {"ok": False, "message": "Client id is required."},
            status=400,
        )
    if not client_id_param.isascii() or not client_id_param.isdigit() or len(client_id_param) > 18:
        return JsonResponse(
            {"ok": False, "message": "Invalid client id."},
            status=400,
        )

    if request.GET.get("years_only") == "1":
        result = list_transaction_years_for_client(request.bookkeeper_account, int(client_id_param))
    else:
        result = list_transactions_for_client_range(
            request.bookkeeper_account, int(client_id_param),
            request.GET.get("date_from"), request.GET.get("date_to"),
        )
    if result.get("ok"):
        return _no_store_json(result)

    return JsonResponse(result, status=_resolve_financial_record_error_status(result))


@require_http_methods(["GET", "POST"])
@require_bookkeeper_auth
def financial_records_api_view(request, client_id):
    if request.method == "GET":
        result = list_records_for_client_period(
            request.bookkeeper_account,
            client_id,
            request.GET.get("month"),
            request.GET.get("year"),
        )
        if result.get("ok"):
            return _no_store_json(result)
        return JsonResponse(result, status=_resolve_financial_record_error_status(result))

    payload = _decode_request_data(request)
    if payload is None:
        return JsonResponse(
            {"ok": False, "message": "Invalid request payload."},
            status=400,
        )

    result = create_record_for_client_period(request.bookkeeper_account, client_id, payload)
    if result.get("ok"):
        return JsonResponse(result, status=201)

    return JsonResponse(result, status=_resolve_financial_record_error_status(result))


@require_http_methods(["GET"])
@require_bookkeeper_auth
def financial_records_last_entry_api_view(request, client_id):
    result = get_last_record_for_client_period(
        request.bookkeeper_account,
        client_id,
        request.GET.get("month"),
        request.GET.get("year"),
        request.GET.get("frequency"),
    )
    if result.get("ok"):
        return JsonResponse(result)

    if result.get("no_record"):
        return JsonResponse(result)

    return JsonResponse(result, status=_resolve_financial_record_error_status(result))


@require_http_methods(["PUT", "PATCH", "DELETE"])
@require_bookkeeper_auth
def financial_record_detail_api_view(request, client_id, record_id):
    if request.method == "DELETE":
        payload = _decode_request_data(request)
        if request.body and payload is None:
            return JsonResponse({"ok": False, "message": "Invalid request payload."}, status=400)
        result = delete_record_for_client(request.bookkeeper_account, client_id, record_id, payload)
        if result.get("ok"):
            return JsonResponse(result)
        return JsonResponse(result, status=_resolve_financial_record_error_status(result))

    payload = _decode_request_data(request)
    if payload is None:
        return JsonResponse(
            {"ok": False, "message": "Invalid request payload."},
            status=400,
        )

    result = update_record_for_client_period(
        request.bookkeeper_account,
        client_id,
        record_id,
        payload,
    )
    if result.get("ok"):
        return JsonResponse(result)

    return JsonResponse(result, status=_resolve_financial_record_error_status(result))


@require_POST
def register_view(request):
    payload = _decode_request_data(request)
    if payload is None:
        return JsonResponse(
            {"ok": False, "message": "Invalid request payload."},
            status=400,
        )

    result = register_user(payload)
    if result.get("ok"):
        user_payload = result.get("user") or {}
        account_id = user_payload.get("id")
        if account_id:
            _set_bookkeeper_session(request, account_id)

        result["redirect_url"] = reverse("verify_email")
        return JsonResponse(result, status=201)

    error_message = result.get("message", "Unable to register account.")
    if error_message in {"Email already exists.", "Username already exists."}:
        return JsonResponse(result, status=409)

    return JsonResponse(result, status=400)


@require_http_methods(["GET"])
@require_bookkeeper_auth
def bookkeeper_audit_log_api_view(request):
    result = list_bookkeeper_audit_logs(
        request.bookkeeper_account,
        (request.GET.get("action") or "").strip(),
        (request.GET.get("search") or "").strip(),
        (request.GET.get("sort") or "").strip(),
    )
    return JsonResponse(result)


@require_POST
def google_complete_signup_view(request):
    google_profile = request.session.get(SESSION_GOOGLE_SIGNUP_PROFILE_KEY)
    if not isinstance(google_profile, dict):
        return JsonResponse(
            {
                "ok": False,
                "message": "Google signup session expired. Please continue with Google again.",
            },
            status=400,
        )

    payload = _decode_request_data(request)
    if payload is None:
        return JsonResponse(
            {"ok": False, "message": "Invalid request payload."},
            status=400,
        )

    result = complete_google_signup(google_profile, payload)
    if result.get("ok"):
        user_payload = result.get("user") or {}
        account_id = user_payload.get("id")
        if account_id:
            _set_bookkeeper_session(request, account_id)
        request.session.pop(SESSION_GOOGLE_SIGNUP_PROFILE_KEY, None)
        request.session.modified = True
        result["redirect_url"] = reverse("pending_approval")
        return JsonResponse(result, status=201)

    error_message = result.get("message", "Unable to create account.")
    if error_message in {
        "Email already exists. Please sign in with Google instead.",
        "Username already exists.",
        "This Google account is already linked to SafeBooks.",
    }:
        return JsonResponse(result, status=409)

    # Field-level validation is a normal form outcome. Keep it out of the
    # server's Bad Request log while still returning ok=false to the UI.
    return JsonResponse(result)


@require_POST
def login_view(request):
    payload = _decode_request_data(request)
    denial = reserve_password_login(
        (payload or {}).get("identifier", ""), request.META.get("REMOTE_ADDR"),
    )
    if denial:
        response = _no_store_json(
            denial, status=429 if denial["error_code"] == "login_rate_limited" else 503,
        )
        if denial.get("retry_after_seconds"):
            response["Retry-After"] = str(denial["retry_after_seconds"])
        return response
    if payload is None:
        return _no_store_json(
            {"ok": False, "message": "Invalid request payload."},
            status=400,
        )

    result = login_user_or_admin(payload)
    if result.get("ok"):
        role = result.get("role")
        user_payload = result.get("user") or {}
        account_id = user_payload.get("id")
        if account_id and role == "admin":
            admin_account = AdminAccount.objects.filter(id=account_id, is_active=True).first()
            if admin_account is None:
                return _no_store_json({
                    "ok": False,
                    "message": "Unable to complete admin login.",
                })

            if not session_auth_hash_matches(admin_account, result.pop("_auth_hash", None)):
                return _no_store_json({"ok": False, "message": "Security settings changed during sign-in. Sign in again."})

            if admin_account.two_factor_enabled:
                if not admin_account.two_factor_secret:
                    _clear_authentication_state(request)
                    return _no_store_json({
                        "ok": False,
                        "message": "Authenticator settings are incomplete. Contact support before signing in.",
                    })
                timeout_seconds, max_attempts, _lockout_seconds = (
                    _admin_two_factor_login_policy()
                )
                failure_count = int(
                    cache.get(_admin_two_factor_failure_cache_key(admin_account.id), 0)
                    or 0
                )
                if failure_count >= max_attempts:
                    _clear_authentication_state(request)
                    return _no_store_json({
                        "ok": False,
                        "message": (
                            "Too many verification attempts. Wait a few minutes "
                            "before trying again."
                        ),
                    })

                _set_admin_two_factor_challenge(request, admin_account)
                return _no_store_json({
                    "ok": True,
                    "message": "Password accepted. Enter your admin verification code.",
                    "role": "admin",
                    "requires_two_factor": True,
                    "challenge_expires_in_seconds": timeout_seconds,
                })

            result = _complete_admin_login(
                request,
                admin_account,
                method="password",
            )
        else:
            result = _finish_bookkeeper_primary_auth(request, result, payload)
        return _no_store_json(result)

    error_message = result.get("message", "Unable to login.")
    if error_message in {
        "Email or username and password are required.",
        "Email or username is required.",
        "Password is required.",
    } or result.get("error_code") in {"missing_credentials", "missing_identifier", "missing_password"}:
        return _no_store_json(result, status=400)

    # Keep expected auth failures as normal API responses to avoid noisy server warnings.
    return _no_store_json(result)


@require_POST
def bookkeeper_two_factor_login_verify_view(request):
    payload = _decode_request_data(request)
    if payload is None:
        return _no_store_json(
            {"ok": False, "message": "Invalid request payload."},
            status=400,
        )

    challenge = request.session.get(SESSION_BOOKKEEPER_TWO_FACTOR_CHALLENGE_KEY)
    if not isinstance(challenge, dict):
        return _no_store_json({
            "ok": False,
            "message": "Your verification session is no longer active. Sign in again.",
            "restart_login": True,
        })

    account_id = _session_timestamp(challenge.get("bookkeeper_id"))
    issued_at = _session_timestamp(challenge.get("issued_at"))
    attempts = max(0, _session_timestamp(challenge.get("attempts")))
    timeout_seconds, max_attempts, lockout_seconds = _bookkeeper_two_factor_login_policy()
    now_timestamp = int(timezone.now().timestamp())

    if (
        account_id <= 0
        or issued_at <= 0
        or issued_at > now_timestamp
        or now_timestamp - issued_at >= timeout_seconds
    ):
        request.session.pop(SESSION_BOOKKEEPER_TWO_FACTOR_CHALLENGE_KEY, None)
        request.session.modified = True
        return _no_store_json({
            "ok": False,
            "message": "Your verification session expired. Sign in again.",
            "restart_login": True,
        })

    cache_key = _bookkeeper_two_factor_failure_cache_key(account_id)
    cached_failures = int(cache.get(cache_key, 0) or 0)
    if attempts >= max_attempts or cached_failures >= max_attempts:
        request.session.pop(SESSION_BOOKKEEPER_TWO_FACTOR_CHALLENGE_KEY, None)
        request.session.modified = True
        return _no_store_json({
            "ok": False,
            "message": "Too many verification attempts. Sign in again after a few minutes.",
            "restart_login": True,
        })

    bookkeeper = BookkeeperAccount.objects.filter(id=account_id).first()
    if (
        bookkeeper is None
        or bookkeeper.status in {BookkeeperAccount.STATUS_REJECTED, BookkeeperAccount.STATUS_SUSPENDED}
        or not bookkeeper.two_factor_enabled
        or not bookkeeper.two_factor_secret
        or not session_auth_hash_matches(bookkeeper, challenge.get("auth_hash"))
    ):
        request.session.pop(SESSION_BOOKKEEPER_TWO_FACTOR_CHALLENGE_KEY, None)
        request.session.modified = True
        return _no_store_json({
            "ok": False,
            "message": "Security settings changed. Sign in again.",
            "restart_login": True,
        })

    code = str(payload.get("code") or "")
    verification = verify_bookkeeper_two_factor_login(bookkeeper, code)
    if not verification.get("ok"):
        attempts += 1
        cached_failures = _increment_two_factor_failures(cache_key, lockout_seconds)
        remaining_attempts = max(0, max_attempts - max(attempts, cached_failures))
        if remaining_attempts == 0:
            request.session.pop(SESSION_BOOKKEEPER_TWO_FACTOR_CHALLENGE_KEY, None)
        else:
            challenge["attempts"] = attempts
            request.session[SESSION_BOOKKEEPER_TWO_FACTOR_CHALLENGE_KEY] = challenge
        request.session.modified = True

        message = verification.get("message") or "Invalid authenticator code."
        if remaining_attempts == 0:
            message = "Too many verification attempts. Sign in again after a few minutes."
        return _no_store_json({
            "ok": False,
            "message": message,
            "remaining_attempts": remaining_attempts,
            "restart_login": remaining_attempts == 0,
        })

    request.session.pop(SESSION_BOOKKEEPER_TWO_FACTOR_CHALLENGE_KEY, None)
    cache.delete(cache_key)
    _set_bookkeeper_session(request, bookkeeper, second_factor_verified=True)
    complete_bookkeeper_login(bookkeeper)

    next_url = _resolve_post_login_redirect(request, {"next_url": challenge.get("next_url")})
    status = bookkeeper.status or BookkeeperAccount.STATUS_APPROVED
    if not bookkeeper.email_verified:
        redirect_url = reverse("verify_email")
    elif status == BookkeeperAccount.STATUS_PENDING:
        redirect_url = reverse("pending_approval")
    else:
        redirect_url = next_url

    return _no_store_json({
        "ok": True,
        "message": "Verification successful. Welcome back!",
        "redirect_url": redirect_url,
        "role": "bookkeeper",
        "user": {
            "id": bookkeeper.id,
            "username": bookkeeper.username,
            "full_name": bookkeeper.full_name,
            "email": bookkeeper.email,
            "status": bookkeeper.status,
            "email_verified": bookkeeper.email_verified,
        },
    })


@require_POST
def admin_two_factor_login_verify_view(request):
    if (
        SESSION_ADMIN_TWO_FACTOR_CHALLENGE_KEY not in request.session
        and SESSION_BOOKKEEPER_TWO_FACTOR_CHALLENGE_KEY in request.session
    ):
        return bookkeeper_two_factor_login_verify_view(request)

    payload = _decode_request_data(request)
    if payload is None:
        return _no_store_json(
            {"ok": False, "message": "Invalid request payload."},
            status=400,
        )

    challenge = request.session.get(SESSION_ADMIN_TWO_FACTOR_CHALLENGE_KEY)
    if not isinstance(challenge, dict):
        return _no_store_json({
            "ok": False,
            "message": "Your verification session is no longer active. Sign in again.",
            "restart_login": True,
        })

    account_id = _session_timestamp(challenge.get("admin_id"))
    issued_at = _session_timestamp(challenge.get("issued_at"))
    attempts = max(0, _session_timestamp(challenge.get("attempts")))
    timeout_seconds, max_attempts, lockout_seconds = _admin_two_factor_login_policy()
    now_timestamp = int(timezone.now().timestamp())

    if (
        account_id <= 0
        or issued_at <= 0
        or issued_at > now_timestamp
        or now_timestamp - issued_at >= timeout_seconds
    ):
        request.session.pop(SESSION_ADMIN_TWO_FACTOR_CHALLENGE_KEY, None)
        request.session.modified = True
        return _no_store_json({
            "ok": False,
            "message": "Your verification session expired. Sign in again.",
            "restart_login": True,
        })

    cache_key = _admin_two_factor_failure_cache_key(account_id)
    cached_failures = int(cache.get(cache_key, 0) or 0)
    if attempts >= max_attempts or cached_failures >= max_attempts:
        request.session.pop(SESSION_ADMIN_TWO_FACTOR_CHALLENGE_KEY, None)
        request.session.modified = True
        return _no_store_json({
            "ok": False,
            "message": "Too many verification attempts. Sign in again after a few minutes.",
            "restart_login": True,
        })

    admin_account = AdminAccount.objects.filter(id=account_id, is_active=True).first()
    if (
        admin_account is None
        or not admin_account.two_factor_enabled
        or not admin_account.two_factor_secret
        or not session_auth_hash_matches(admin_account, challenge.get("auth_hash"))
    ):
        request.session.pop(SESSION_ADMIN_TWO_FACTOR_CHALLENGE_KEY, None)
        request.session.modified = True
        return _no_store_json({
            "ok": False,
            "message": "Admin security settings changed. Sign in again.",
            "restart_login": True,
        })

    verification = verify_admin_two_factor_login(
        admin_account,
        str(payload.get("code") or ""),
    )
    if not verification.get("ok"):
        attempts += 1
        cached_failures = _increment_two_factor_failures(cache_key, lockout_seconds)
        remaining_attempts = max(0, max_attempts - max(attempts, cached_failures))

        if remaining_attempts == 0:
            request.session.pop(SESSION_ADMIN_TWO_FACTOR_CHALLENGE_KEY, None)
        else:
            challenge["attempts"] = attempts
            request.session[SESSION_ADMIN_TWO_FACTOR_CHALLENGE_KEY] = challenge
        request.session.modified = True

        message = verification.get("message") or "Invalid authenticator or recovery code."
        if remaining_attempts == 0:
            message = "Too many verification attempts. Sign in again after a few minutes."
        return _no_store_json({
            "ok": False,
            "message": message,
            "remaining_attempts": remaining_attempts,
            "restart_login": remaining_attempts == 0,
        })

    cache.delete(cache_key)
    recovery_code_used = bool(verification.get("recovery_code_used"))
    result = _complete_admin_login(
        request,
        admin_account,
        method="recovery_code" if recovery_code_used else "authenticator",
    )
    result["recovery_code_used"] = recovery_code_used
    if recovery_code_used:
        result["message"] = "Login successful. That recovery code has now been used."
    return _no_store_json(result)


@require_POST
@require_bookkeeper_auth
def resend_email_verification_api_view(request):
    result = send_email_verification_code(request.bookkeeper_account, force=False)
    if result.get("ok"):
        return JsonResponse(result)

    status_code = 400
    if "retry_after_seconds" in result:
        status_code = 429
    return JsonResponse(result, status=status_code)


@require_POST
@require_bookkeeper_auth
def verify_email_api_view(request):
    payload = _decode_request_data(request)
    if payload is None:
        return JsonResponse(
            {"ok": False, "message": "Invalid request payload."},
            status=400,
        )

    code = payload.get("code") or payload.get("verification_code")
    result = verify_email_code(request.bookkeeper_account, code)
    if result.get("ok"):
        status = request.bookkeeper_account.status or BookkeeperAccount.STATUS_PENDING
        if status == BookkeeperAccount.STATUS_PENDING:
            result["redirect_url"] = reverse("pending_approval")
        else:
            result["redirect_url"] = reverse("dashboard")
        return JsonResponse(result)

    return JsonResponse(result, status=400)


@require_POST
@require_any_auth
def logout_view(request):
    admin_account = _get_session_admin(request)
    try:
        if admin_account is not None:
            with transaction.atomic():
                record_admin_auth_event(admin_account, AdminAuditLog.ACTION_ADMIN_LOGOUT)
    except Exception as error:
        logger.warning("Logout audit could not be saved (%s).", type(error).__name__)
    try:
        request.session.flush()
    except DatabaseError as error:
        logger.error("Session logout could not be confirmed (%s).", type(error).__name__)
        return _no_store_json({"ok": False, "message": "Logout could not be confirmed. Please retry."}, status=503)
    return JsonResponse(
        {
            "ok": True,
            "message": "Logged out successfully.",
            "redirect_url": reverse("login"),
        }
    )


@require_POST
def forgot_password_send_code_api_view(request):
    payload = _decode_request_data(request)
    if payload is None:
        return _no_store_json(
            {"ok": False, "message": "Invalid request payload."},
            status=400,
        )

    email = payload.get("email")
    request.session.pop(SESSION_PASSWORD_RESET_AUTHORIZATION_KEY, None)
    from safebooks.services.auth_service import send_password_reset_code
    result = send_password_reset_code(email)
    if result.get("ok"):
        return _no_store_json(result)

    return _no_store_json(result, status=400)


@require_POST
def forgot_password_verify_code_api_view(request):
    payload = _decode_request_data(request)
    if payload is None:
        return _no_store_json(
            {"ok": False, "message": "Invalid request payload."},
            status=400,
        )

    email = payload.get("email")
    code = payload.get("code")
    request.session.pop(SESSION_PASSWORD_RESET_AUTHORIZATION_KEY, None)
    from safebooks.services.auth_service import verify_password_reset_code
    result = verify_password_reset_code(email, code)
    # This proof is internal authorization, never a JSON field supplied by or
    # returned to the browser. Rotate the session when verification succeeds.
    reset_authorization = result.pop("reset_authorization", None)
    if result.get("ok"):
        request.session.cycle_key()
        request.session[SESSION_PASSWORD_RESET_AUTHORIZATION_KEY] = {
            "email": str(email or "").strip().lower(),
            "token": reset_authorization,
        }
        return _no_store_json(result)

    return _no_store_json(result, status=400)


@require_POST
def forgot_password_reset_api_view(request):
    payload = _decode_request_data(request)
    if payload is None:
        return _no_store_json(
            {"ok": False, "message": "Invalid request payload."},
            status=400,
        )

    email = payload.get("email")
    new_password = payload.get("new_password")
    confirm_password = payload.get("confirm_password")
    authorization = request.session.get(SESSION_PASSWORD_RESET_AUTHORIZATION_KEY)
    reset_authorization = ""
    if isinstance(authorization, dict) and authorization.get("email") == str(email or "").strip().lower():
        reset_authorization = authorization.get("token")
    from safebooks.services.auth_service import confirm_password_reset
    result = confirm_password_reset(
        email, new_password, confirm_password, reset_authorization=reset_authorization
    )
    if result.get("ok"):
        request.session.pop(SESSION_PASSWORD_RESET_AUTHORIZATION_KEY, None)
        return _no_store_json(result)

    return _no_store_json(result, status=400)
