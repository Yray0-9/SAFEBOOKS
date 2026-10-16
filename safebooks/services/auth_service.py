from datetime import timedelta
from hashlib import sha256
import json
import logging
import secrets
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.core.cache import cache
from django.core.mail import send_mail
from django.db import IntegrityError, transaction
from django.db.models import F, Q
from django.utils import timezone

from safebooks.models import AdminAccount, BookkeeperAccount
from safebooks.services.session_security_service import account_session_auth_hash
from safebooks.validators.password_validator import missing_password_requirements
from safebooks.validators.data_validator import model_text_errors
from safebooks.services.email_delivery_service import email_count_confirmed, LOCAL_EMAIL_BACKENDS


AUTH_FAILURE_MESSAGE = "Invalid email or username, or password."
logger = logging.getLogger(__name__)
AUTH_INACTIVE_ACCOUNT_MESSAGE = "This account is inactive. Please contact support."
GOOGLE_AUTHORIZATION_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_TOKENINFO_URL = "https://oauth2.googleapis.com/tokeninfo"
GOOGLE_OAUTH_TIMEOUT_SECONDS = 10


def _create_bookkeeper_with_unique_checks(values):
    try:
        with transaction.atomic():
            return BookkeeperAccount.objects.create(**values), None
    except IntegrityError:
        # Uniqueness can change after the friendly pre-check; query after rollback.
        for field, message in (("email", "Email already exists."), ("username", "Username already exists."),
                               ("google_sub", "This Google account is already linked to SafeBooks.")):
            value = values.get(field)
            if value and BookkeeperAccount.objects.filter(**{f"{field}__iexact": value}).exists():
                return None, {"ok": False, "message": message, "errors": [message]}
        message = "Unable to create the account. Refresh and try again."
        return None, {"ok": False, "message": message, "errors": [message]}

EMAIL_VERIFICATION_CODE_LENGTH = 6
DEFAULT_VERIFICATION_TTL_MINUTES = 10
DEFAULT_VERIFICATION_RESEND_COOLDOWN_SECONDS = 60
CONSOLE_EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
FILE_EMAIL_BACKEND = "django.core.mail.backends.filebased.EmailBackend"
EMAIL_VERIFICATION_CACHE_PREFIX = "safebooks:email-verification"
EMAIL_VERIFICATION_CACHE_CODE_SUFFIX = "code"
EMAIL_VERIFICATION_CACHE_SENT_SUFFIX = "sent"

PASSWORD_RESET_CACHE_PREFIX = "safebooks:password-reset"
PASSWORD_RESET_CACHE_CODE_SUFFIX = "code"
PASSWORD_RESET_CACHE_SENT_SUFFIX = "sent"
PASSWORD_RESET_CACHE_VERIFIED_SUFFIX = "verified"
PASSWORD_RESET_AUTHORIZATION_TTL_SECONDS = 5 * 60


def _get_google_client_id() -> str:
    return str(getattr(settings, "SAFEBOOKS_GOOGLE_OAUTH_CLIENT_ID", "") or "").strip()


def _get_google_client_secret() -> str:
    return str(getattr(settings, "SAFEBOOKS_GOOGLE_OAUTH_CLIENT_SECRET", "") or "").strip()


def is_google_oauth_configured() -> bool:
    return bool(_get_google_client_id() and _get_google_client_secret())


def build_google_oauth_authorization_url(redirect_uri: str, state: str) -> str:
    params = {
        "client_id": _get_google_client_id(),
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "access_type": "online",
        "prompt": "select_account",
    }
    return f"{GOOGLE_AUTHORIZATION_URL}?{urlencode(params)}"


def _post_google_token_request(code: str, redirect_uri: str) -> dict:
    payload = urlencode({
        "code": code,
        "client_id": _get_google_client_id(),
        "client_secret": _get_google_client_secret(),
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    }).encode("utf-8")

    request = Request(
        GOOGLE_TOKEN_URL,
        data=payload,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )

    with urlopen(request, timeout=GOOGLE_OAUTH_TIMEOUT_SECONDS) as response:
        return json.loads(response.read().decode("utf-8"))


def _get_google_tokeninfo(id_token: str) -> dict:
    request = Request(
        f"{GOOGLE_TOKENINFO_URL}?{urlencode({'id_token': id_token})}",
        method="GET",
    )
    with urlopen(request, timeout=GOOGLE_OAUTH_TIMEOUT_SECONDS) as response:
        return json.loads(response.read().decode("utf-8"))


def exchange_google_oauth_code(code: str, redirect_uri: str) -> dict:
    if not is_google_oauth_configured():
        return {
            "ok": False,
            "message": "Google sign-in is not configured yet.",
        }

    code_value = str(code or "").strip()
    if not code_value:
        return {
            "ok": False,
            "message": "Google sign-in was cancelled or incomplete.",
        }

    try:
        token_payload = _post_google_token_request(code_value, redirect_uri)
        id_token = str(token_payload.get("id_token") or "").strip()
        if not id_token:
            return {
                "ok": False,
                "message": "Google did not return a valid identity token.",
            }

        tokeninfo = _get_google_tokeninfo(id_token)
    except (HTTPError, URLError, TimeoutError, ValueError, json.JSONDecodeError):
        return {
            "ok": False,
            "message": "Unable to verify Google sign-in. Please try again.",
        }

    audience = str(tokeninfo.get("aud") or "").strip()
    issuer = str(tokeninfo.get("iss") or "").strip()
    email = str(tokeninfo.get("email") or "").strip().lower()
    email_verified = str(tokeninfo.get("email_verified") or "").lower() == "true"
    google_sub = str(tokeninfo.get("sub") or "").strip()
    full_name = str(tokeninfo.get("name") or "").strip()

    if audience != _get_google_client_id() or issuer not in {"accounts.google.com", "https://accounts.google.com"}:
        return {
            "ok": False,
            "message": "Google sign-in could not be verified.",
        }

    if not google_sub or not email:
        return {
            "ok": False,
            "message": "Google did not return the required account details.",
        }

    if not email_verified:
        return {
            "ok": False,
            "message": "Your Google email must be verified before using SafeBooks.",
        }

    return {
        "ok": True,
        "profile": {
            "google_sub": google_sub,
            "email": email,
            "full_name": full_name,
            "email_verified": True,
        },
    }


def _build_bookkeeper_payload(account: BookkeeperAccount) -> dict:
    return {
        "id": account.id,
        "full_name": account.full_name,
        "email": account.email,
        "username": account.username,
        "status": account.status or BookkeeperAccount.STATUS_PENDING,
        "email_verified": bool(account.email_verified),
        "login_alerts_enabled": bool(getattr(account, "login_alerts_enabled", False)),
    }


def authenticate_google_bookkeeper(profile: dict) -> dict:
    google_sub = str(profile.get("google_sub") or "").strip()
    email = str(profile.get("email") or "").strip().lower()

    if not google_sub or not email:
        return {
            "ok": False,
            "message": "Google account details are incomplete.",
        }

    account = BookkeeperAccount.objects.filter(google_sub=google_sub).first()
    if account is None:
        account = BookkeeperAccount.objects.filter(email__iexact=email).first()

    if account is None:
        return {
            "ok": True,
            "requires_signup_completion": True,
            "message": "Complete your SafeBooks account setup.",
            "profile": {
                "email": email,
                "full_name": str(profile.get("full_name") or "").strip(),
            },
        }

    if account.google_sub and account.google_sub != google_sub:
        return {
            "ok": False,
            "message": "This email is already linked to another Google account.",
        }

    update_fields: list[str] = []
    if not account.google_sub:
        account.google_sub = google_sub
        update_fields.append("google_sub")

    if not account.email_verified:
        account.email_verified = True
        update_fields.append("email_verified")

    status = account.status or BookkeeperAccount.STATUS_PENDING
    if status == BookkeeperAccount.STATUS_REJECTED:
        return {
            "ok": False,
            "message": "Account was not approved. Contact support for help.",
            "status": status,
        }

    if status == BookkeeperAccount.STATUS_SUSPENDED:
        return {
            "ok": False,
            "message": "Account is suspended. Contact support for help.",
            "status": status,
        }

    if status == BookkeeperAccount.STATUS_PENDING:
        if update_fields:
            account.save(update_fields=update_fields)
        return {
            "ok": True,
            "message": "Account pending approval. You will get access once approved.",
            "user": _build_bookkeeper_payload(account),
            "role": "bookkeeper",
            "_auth_hash": account_session_auth_hash(account),
        }

    if update_fields:
        account.save(update_fields=update_fields)

    return {
        "ok": True,
        "message": "Google sign-in successful.",
        "user": _build_bookkeeper_payload(account),
        "role": "bookkeeper",
        "_auth_hash": account_session_auth_hash(account),
    }


def complete_google_signup(profile: dict, data: dict) -> dict:
    google_sub = str(profile.get("google_sub") or "").strip()
    email = str(profile.get("email") or "").strip().lower()
    full_name = str(data.get("full_name") or profile.get("full_name") or "").strip()
    username = str(data.get("username") or "").strip()
    password = str(data.get("password") or "")
    confirm_password = str(data.get("confirm_password") or "")

    errors: list[str] = []
    if not google_sub or not email:
        errors.append("Google signup session expired. Please continue with Google again.")
    if not full_name:
        errors.append("Full name is required.")
    if not username:
        errors.append("Username is required.")
    if not password:
        errors.append("Password is required.")
    if password and password != confirm_password:
        errors.append("Passwords do not match.")

    password_requirement_errors = missing_password_requirements(password)
    if password and password_requirement_errors:
        errors.append("Password does not meet requirements.")

    errors.extend(model_text_errors(BookkeeperAccount, {
        **data, "google_sub": google_sub, "email": email,
        "full_name": data.get("full_name") or profile.get("full_name"),
    }))

    if errors:
        return {
            "ok": False,
            "message": errors[0],
            "errors": errors,
            "password_requirements": password_requirement_errors,
        }

    if BookkeeperAccount.objects.filter(email__iexact=email).exists():
        return {
            "ok": False,
            "message": "Email already exists. Please sign in with Google instead.",
            "errors": ["Email already exists."],
        }

    if BookkeeperAccount.objects.filter(username__iexact=username).exists():
        return {
            "ok": False,
            "message": "Username already exists.",
            "errors": ["Username already exists."],
        }

    if BookkeeperAccount.objects.filter(google_sub=google_sub).exists():
        return {
            "ok": False,
            "message": "This Google account is already linked to SafeBooks.",
            "errors": ["This Google account is already linked to SafeBooks."],
        }

    account, create_error = _create_bookkeeper_with_unique_checks({
        "full_name": full_name, "email": email, "username": username, "google_sub": google_sub,
        "password_hash": make_password(password), "status": BookkeeperAccount.STATUS_PENDING, "email_verified": True,
    })
    if create_error:
        if create_error["message"] == "Email already exists.":
            create_error["message"] = "Email already exists. Please sign in with Google instead."
        return create_error

    return {
        "ok": True,
        "message": "SafeBooks account created. Your account is pending admin approval.",
        "user": _build_bookkeeper_payload(account),
        "role": "bookkeeper",
    }


def _password_reset_cache_key(email: str, suffix: str) -> str:
    normalized = str(email or "").strip().lower()
    return f"{PASSWORD_RESET_CACHE_PREFIX}:{normalized}:{suffix}"


def _get_setting_int(setting_name: str, default_value: int) -> int:
    raw_value = getattr(settings, setting_name, None)
    if raw_value is None:
        return default_value
    try:
        return int(raw_value)
    except (TypeError, ValueError):
        return default_value


def _get_verification_ttl_minutes() -> int:
    return _get_setting_int(
        "SAFEBOOKS_EMAIL_VERIFICATION_CODE_TTL_MINUTES",
        DEFAULT_VERIFICATION_TTL_MINUTES,
    )


def _get_verification_resend_cooldown_seconds() -> int:
    return _get_setting_int(
        "SAFEBOOKS_EMAIL_VERIFICATION_RESEND_COOLDOWN_SECONDS",
        DEFAULT_VERIFICATION_RESEND_COOLDOWN_SECONDS,
    )


def _should_expose_debug_code() -> bool:
    if not getattr(settings, "DEBUG", False):
        return False

    backend = getattr(settings, "EMAIL_BACKEND", "")
    return backend in {CONSOLE_EMAIL_BACKEND, FILE_EMAIL_BACKEND}


def _email_verification_cache_key(account_id: int, suffix: str) -> str:
    return f"{EMAIL_VERIFICATION_CACHE_PREFIX}:{account_id}:{suffix}"


def _generate_verification_code(length: int) -> str:
    if length <= 0:
        length = EMAIL_VERIFICATION_CODE_LENGTH
    max_value = 10 ** length
    return f"{secrets.randbelow(max_value):0{length}d}"


def _build_verification_email(account: BookkeeperAccount, code: str, ttl_minutes: int) -> tuple[str, str]:
    recipient_name = (account.full_name or "").strip() or "there"
    subject = "SafeBooks email verification"
    message = (
        f"Hi {recipient_name},\n\n"
        f"Your SafeBooks verification code is {code}.\n"
        f"This code expires in {ttl_minutes} minutes.\n\n"
        "If you did not create a SafeBooks account, you can ignore this message.\n\n"
        "SafeBooks"
    )
    return subject, message


def _build_login_alert_email(account: BookkeeperAccount, login_time: timezone.datetime) -> tuple[str, str]:
    recipient_name = (account.full_name or "").strip() or "there"
    formatted_time = timezone.localtime(login_time).strftime("%Y-%m-%d %H:%M")
    subject = "SafeBooks login alert"
    message = (
        f"Hi {recipient_name},\n\n"
        "We detected a new sign-in to your SafeBooks account.\n"
        f"Time: {formatted_time}\n\n"
        "If this was you, no action is needed. If not, please reset your password.\n\n"
        "SafeBooks"
    )
    return subject, message


def _maybe_send_login_alert(account: BookkeeperAccount) -> None:
    if not getattr(account, "login_alerts_enabled", False):
        return
    if not getattr(account, "email", ""):
        return

    try:
        subject, message = _build_login_alert_email(account, timezone.now())
        sent_count = send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [account.email],
            fail_silently=False,
        )
        if not email_count_confirmed(sent_count):
            logger.warning("Login alert was not accepted by the email backend.")
    except Exception as error:
        # Avoid blocking logins if email delivery fails.
        logger.warning("Login alert failed (%s).", type(error).__name__)
        return


def complete_bookkeeper_login(account: BookkeeperAccount) -> None:
    """Record a sign-in only after all configured factors have succeeded."""
    if account.email_verified and account.status == BookkeeperAccount.STATUS_APPROVED:
        account.last_login = timezone.now()
        account.save(update_fields=["last_login"])
        _maybe_send_login_alert(account)


def send_email_verification_code(account: BookkeeperAccount, force: bool = False) -> dict:
    if account.email_verified:
        return {
            "ok": False,
            "message": "Email is already verified.",
        }

    if account.id is None:
        return {
            "ok": False,
            "message": "Unable to send verification email."
        }

    now = timezone.now()
    now_ts = int(now.timestamp())
    cooldown_seconds = _get_verification_resend_cooldown_seconds()
    sent_key = _email_verification_cache_key(account.id, EMAIL_VERIFICATION_CACHE_SENT_SUFFIX)
    last_sent_ts = cache.get(sent_key)
    if last_sent_ts is not None:
        try:
            last_sent_ts = int(last_sent_ts)
        except (TypeError, ValueError):
            last_sent_ts = None

    if not force and last_sent_ts is not None:
        elapsed = now_ts - last_sent_ts
        if elapsed < cooldown_seconds:
            return {
                "ok": False,
                "message": "Please wait before requesting another code.",
                "retry_after_seconds": int(cooldown_seconds - elapsed),
            }

    ttl_minutes = _get_verification_ttl_minutes()
    code = _generate_verification_code(EMAIL_VERIFICATION_CODE_LENGTH)
    subject, message = _build_verification_email(account, code, ttl_minutes)

    try:
        sent_count = send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [account.email],
            fail_silently=False,
        )
        if not email_count_confirmed(sent_count):
            return {"ok": False, "message": "The email backend did not accept the verification email. Please try again later."}
    except Exception:
        return {
            "ok": False,
            "message": "Unable to send verification email. Please try again later.",
        }

    ttl_seconds = int(timedelta(minutes=ttl_minutes).total_seconds())
    expires_ts = now_ts + ttl_seconds
    code_key = _email_verification_cache_key(account.id, EMAIL_VERIFICATION_CACHE_CODE_SUFFIX)

    cache.set(
        code_key,
        {"hash": make_password(code), "expires_at": expires_ts},
        timeout=ttl_seconds,
    )
    cache.set(sent_key, now_ts, timeout=cooldown_seconds)

    result = {
        "ok": True,
        "message": "Verification code prepared locally; no inbox delivery." if settings.EMAIL_BACKEND in LOCAL_EMAIL_BACKENDS else "Verification email accepted for delivery. Check your inbox or spam folder.",
        "retry_after_seconds": cooldown_seconds,
    }

    if _should_expose_debug_code():
        result["debug_code"] = code

    return result


def verify_email_code(account: BookkeeperAccount, code: str) -> dict:
    if account.email_verified:
        return {
            "ok": True,
            "message": "Email is already verified.",
        }

    if account.id is None:
        return {
            "ok": False,
            "message": "Unable to verify email."
        }

    code_value = str(code or "").strip()
    if not code_value:
        return {
            "ok": False,
            "message": "Verification code is required.",
        }

    code_key = _email_verification_cache_key(account.id, EMAIL_VERIFICATION_CACHE_CODE_SUFFIX)
    sent_key = _email_verification_cache_key(account.id, EMAIL_VERIFICATION_CACHE_SENT_SUFFIX)
    payload = cache.get(code_key)
    if not isinstance(payload, dict):
        return {
            "ok": False,
            "message": "No verification code found. Please request a new code.",
        }

    code_hash = str(payload.get("hash") or "")
    expires_ts = payload.get("expires_at")
    if expires_ts is not None:
        try:
            expires_ts = int(expires_ts)
        except (TypeError, ValueError):
            expires_ts = None

    now_ts = int(timezone.now().timestamp())
    if expires_ts is not None and now_ts > expires_ts:
        cache.delete(code_key)
        return {
            "ok": False,
            "message": "Verification code has expired. Request a new one.",
            "code_expired": True,
        }

    if not code_hash or not check_password(code_value, code_hash):
        return {
            "ok": False,
            "message": "Invalid verification code.",
        }

    account.email_verified = True
    account.save(update_fields=["email_verified"])
    cache.delete(code_key)
    cache.delete(sent_key)

    return {
        "ok": True,
        "message": "Email verified successfully.",
    }


def _looks_like_supported_hash(password_hash: str) -> bool:
    normalized_hash = str(password_hash or "")
    return normalized_hash.startswith((
        "pbkdf2_",
        "argon2$",
        "bcrypt$",
        "bcrypt_sha256$",
        "scrypt$",
    ))


def register_user(data: dict) -> dict:
    full_name = str(data.get("full_name") or "").strip()
    email = str(data.get("email") or "").strip()
    username = str(data.get("username") or "").strip()
    password = str(data.get("password", ""))
    confirm_password = str(data.get("confirm_password", ""))

    errors: list[str] = []

    if not full_name:
        errors.append("Full name is required.")
    if not email:
        errors.append("Email is required.")
    if not username:
        errors.append("Username is required.")
    if not password:
        errors.append("Password is required.")
    if password and password != confirm_password:
        errors.append("Passwords do not match.")

    password_requirement_errors = missing_password_requirements(password)
    if password and password_requirement_errors:
        errors.append("Password does not meet requirements.")

    errors.extend(model_text_errors(BookkeeperAccount, data))

    if errors:
        return {
            "ok": False,
            "message": errors[0],
            "errors": errors,
            "password_requirements": password_requirement_errors,
        }

    if BookkeeperAccount.objects.filter(email__iexact=email).exists():
        return {
            "ok": False,
            "message": "Email already exists.",
            "errors": ["Email already exists."],
        }

    if BookkeeperAccount.objects.filter(username__iexact=username).exists():
        return {
            "ok": False,
            "message": "Username already exists.",
            "errors": ["Username already exists."],
        }

    account, create_error = _create_bookkeeper_with_unique_checks({
        "full_name": full_name, "email": email, "username": username,
        "password_hash": make_password(password), "status": BookkeeperAccount.STATUS_PENDING, "email_verified": False,
    })
    if create_error:
        return create_error

    verification_result = send_email_verification_code(account, force=True)
    verification_sent = verification_result.get("ok", False)
    if verification_sent:
        message = "Account created successfully. Verify your email to continue."
    else:
        message = "Account created successfully. We could not send a verification email. Please request a new code."

    return {
        "ok": True,
        "message": message,
        "verification_email_sent": verification_sent,
        "user": {
            "id": account.id,
            "full_name": account.full_name,
            "email": account.email,
            "username": account.username,
            "status": account.status,
            "email_verified": account.email_verified,
        },
    }


def _invalid_login_credentials() -> dict:
    # One public result for missing accounts and failed passwords, for both roles.
    return {
        "ok": False, "message": AUTH_FAILURE_MESSAGE, "errors": [AUTH_FAILURE_MESSAGE],
        "field": "both", "error_code": "invalid_credentials",
    }


def login_user(data: dict) -> dict:
    identifier = str(data.get("identifier", "")).strip()
    password = str(data.get("password", ""))

    if not identifier and not password:
        return {
            "ok": False,
            "message": "Email or username and password are required.",
            "errors": ["Email or username and password are required."],
            "field": "both",
            "error_code": "missing_credentials",
        }
    if not identifier:
        return {
            "ok": False,
            "message": "Email or username is required.",
            "errors": ["Email or username is required."],
            "field": "identifier",
            "error_code": "missing_identifier",
        }
    if not password:
        return {
            "ok": False,
            "message": "Password is required.",
            "errors": ["Password is required."],
            "field": "password",
            "error_code": "missing_password",
        }

    account = BookkeeperAccount.objects.filter(
        Q(email__iexact=identifier) | Q(username__iexact=identifier)
    ).first()

    if account is None:
        # Django's default authentication backend performs equivalent hash work
        # on unknown users. Avoid an immediate, noticeably cheaper rejection.
        make_password(password)
        return _invalid_login_credentials()

    stored_password_hash = str(account.password_hash or "")
    is_authenticated = check_password(password, stored_password_hash)

    # Backward compatibility for early records that stored raw passwords.
    if not is_authenticated and stored_password_hash and not _looks_like_supported_hash(stored_password_hash):
        if password == stored_password_hash:
            is_authenticated = True
            account.password_hash = make_password(password)
            account.save(update_fields=["password_hash"])

    if not is_authenticated:
        return _invalid_login_credentials()

    status = account.status or BookkeeperAccount.STATUS_PENDING
    if status == BookkeeperAccount.STATUS_REJECTED:
        message = "Account was not approved. Contact support for help."
        return {
            "ok": False,
            "message": message,
            "errors": [message],
            "status": status,
        }

    if status == BookkeeperAccount.STATUS_SUSPENDED:
        message = "Account is suspended. Contact support for help."
        return {
            "ok": False,
            "message": message,
            "errors": [message],
            "status": status,
        }

    login_alerts_enabled = bool(getattr(account, "login_alerts_enabled", False))

    if not account.email_verified:
        return {
            "ok": True,
            "message": "Email verification required. Check your inbox for a 6-digit code.",
            "requires_email_verification": True,
            "_auth_hash": account_session_auth_hash(account),
            "user": {
                "id": account.id,
                "full_name": account.full_name,
                "email": account.email,
                "username": account.username,
                "status": status,
                "email_verified": False,
                "login_alerts_enabled": login_alerts_enabled,
            },
        }

    if status == BookkeeperAccount.STATUS_PENDING:
        return {
            "ok": True,
            "message": "Account pending approval. You will get access once approved.",
            "_auth_hash": account_session_auth_hash(account),
            "user": {
                "id": account.id,
                "full_name": account.full_name,
                "email": account.email,
                "username": account.username,
                "status": status,
                "email_verified": True,
                "login_alerts_enabled": login_alerts_enabled,
            },
        }

    return {
        "ok": True,
        "message": "Login successful.",
        "_auth_hash": account_session_auth_hash(account),
        "user": {
            "id": account.id,
            "full_name": account.full_name,
            "email": account.email,
            "username": account.username,
            "status": status,
            "email_verified": True,
            "login_alerts_enabled": login_alerts_enabled,
        },
    }


def _login_admin_account(account: AdminAccount, password: str) -> dict:
    stored_password_hash = str(account.password_hash or "")
    is_authenticated = check_password(password, stored_password_hash)

    if not is_authenticated and stored_password_hash and not _looks_like_supported_hash(stored_password_hash):
        if password == stored_password_hash:
            is_authenticated = True
            account.password_hash = make_password(password)

    if not is_authenticated:
        return _invalid_login_credentials()

    # Account status is private until the submitted password has been verified.
    if not account.is_active:
        return {
            "ok": False, "message": AUTH_INACTIVE_ACCOUNT_MESSAGE,
            "errors": [AUTH_INACTIVE_ACCOUNT_MESSAGE], "field": "identifier",
            "error_code": "account_inactive",
        }

    # A valid password is not a completed admin sign-in when a second factor
    # is enabled. The view records last_login after the full flow succeeds.
    if account.password_hash != stored_password_hash:
        account.save(update_fields=["password_hash"])

    return {
        "ok": True,
        "message": "Login successful.",
        "user": {
            "id": account.id,
            "full_name": account.full_name,
            "email": account.email,
        },
        "role": "admin",
        "_auth_hash": account_session_auth_hash(account),
    }


def login_user_or_admin(data: dict) -> dict:
    identifier = str(data.get("identifier", "")).strip()
    password = str(data.get("password", ""))

    if not identifier and not password:
        return {
            "ok": False,
            "message": "Email or username and password are required.",
            "errors": ["Email or username and password are required."],
            "field": "both",
            "error_code": "missing_credentials",
        }
    if not identifier:
        return {
            "ok": False,
            "message": "Email or username is required.",
            "errors": ["Email or username is required."],
            "field": "identifier",
            "error_code": "missing_identifier",
        }
    if not password:
        return {
            "ok": False,
            "message": "Password is required.",
            "errors": ["Password is required."],
            "field": "password",
            "error_code": "missing_password",
        }

    admin_account = AdminAccount.objects.filter(email__iexact=identifier).first()
    if admin_account is not None:
        return _login_admin_account(admin_account, password)

    result = login_user(data)
    if result.get("ok"):
        result["role"] = "bookkeeper"
    return result


def send_password_reset_code(email: str) -> dict:
    normalized_email = str(email or "").strip().lower()
    if not normalized_email:
        return {
            "ok": False,
            "message": "Email address is required.",
        }

    account = BookkeeperAccount.objects.filter(email__iexact=normalized_email).first()
    if account is None:
        return {
            "ok": False,
            "message": "Email address not found.",
        }

    now = timezone.now()
    now_ts = int(now.timestamp())
    cooldown_seconds = _get_verification_resend_cooldown_seconds()
    sent_key = _password_reset_cache_key(normalized_email, PASSWORD_RESET_CACHE_SENT_SUFFIX)
    last_sent_ts = cache.get(sent_key)
    if last_sent_ts is not None:
        try:
            last_sent_ts = int(last_sent_ts)
        except (TypeError, ValueError):
            last_sent_ts = None

    if last_sent_ts is not None:
        elapsed = now_ts - last_sent_ts
        if elapsed < cooldown_seconds:
            return {
                "ok": False,
                "message": "Please wait before requesting another code.",
                "retry_after_seconds": int(cooldown_seconds - elapsed),
            }

    ttl_minutes = _get_verification_ttl_minutes()
    code = _generate_verification_code(EMAIL_VERIFICATION_CODE_LENGTH)

    recipient_name = (account.full_name or "").strip() or "there"
    subject = "SafeBooks password reset"
    message = (
        f"Hi {recipient_name},\n\n"
        f"Your SafeBooks password reset code is {code}.\n"
        f"This code expires in {ttl_minutes} minutes.\n\n"
        "If you did not request a password reset, you can safely ignore this email.\n\n"
        "SafeBooks"
    )

    try:
        sent_count = send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [account.email],
            fail_silently=False,
        )
        if not email_count_confirmed(sent_count):
            return {"ok": False, "message": "The email backend did not accept the password reset email. Please try again later."}
    except Exception:
        return {
            "ok": False,
            "message": "Unable to send password reset email. Please try again later.",
        }

    ttl_seconds = int(timedelta(minutes=ttl_minutes).total_seconds())
    code_key = _password_reset_cache_key(normalized_email, PASSWORD_RESET_CACHE_CODE_SUFFIX)

    # A newly issued code replaces any previous reset authorization for this account.
    cache.delete(_password_reset_cache_key(normalized_email, PASSWORD_RESET_CACHE_VERIFIED_SUFFIX))
    cache.set(
        code_key,
        {"hash": make_password(code), "expires_at": now_ts + ttl_seconds},
        timeout=ttl_seconds,
    )
    cache.set(sent_key, now_ts, timeout=cooldown_seconds)

    result = {
        "ok": True,
        "message": "Password reset code prepared locally; no inbox delivery." if settings.EMAIL_BACKEND in LOCAL_EMAIL_BACKENDS else "Password reset email accepted for delivery. Check your inbox or spam folder.",
        "retry_after_seconds": cooldown_seconds,
    }

    if _should_expose_debug_code():
        result["debug_code"] = code

    return result


def verify_password_reset_code(email: str, code: str) -> dict:
    normalized_email = str(email or "").strip().lower()
    if not normalized_email:
        return {
            "ok": False,
            "message": "Email address is required.",
        }

    code_value = str(code or "").strip()
    if not code_value:
        return {
            "ok": False,
            "message": "Verification code is required.",
        }

    code_key = _password_reset_cache_key(normalized_email, PASSWORD_RESET_CACHE_CODE_SUFFIX)
    payload = cache.get(code_key)
    if not isinstance(payload, dict):
        return {
            "ok": False,
            "message": "No password reset code found or code has expired. Request a new one.",
        }

    code_hash = str(payload.get("hash") or "")
    expires_ts = payload.get("expires_at")
    if expires_ts is not None:
        try:
            expires_ts = int(expires_ts)
        except (TypeError, ValueError):
            expires_ts = None

    now_ts = int(timezone.now().timestamp())
    if expires_ts is None or now_ts >= expires_ts:
        cache.delete(code_key)
        return {
            "ok": False,
            "message": "Verification code has expired. Request a new one.",
        }

    if not code_hash or not check_password(code_value, code_hash):
        return {
            "ok": False,
            "message": "Invalid verification code.",
        }

    account = BookkeeperAccount.objects.filter(email__iexact=normalized_email).first()
    if account is None:
        return {"ok": False, "message": "Account not found."}

    # Email-wide verification alone must never authorize a password change. The
    # view keeps this unpredictable proof in the verifying browser's server-side session.
    reset_authorization = secrets.token_urlsafe(32)
    verified_key = _password_reset_cache_key(normalized_email, PASSWORD_RESET_CACHE_VERIFIED_SUFFIX)
    cache.set(
        verified_key,
        {
            "account_id": account.id,
            "authorization_digest": sha256(reset_authorization.encode()).hexdigest(),
            "password_hash": account.password_hash,
            "session_version": account.session_version,
            "expires_at": now_ts + PASSWORD_RESET_AUTHORIZATION_TTL_SECONDS,
        },
        timeout=PASSWORD_RESET_AUTHORIZATION_TTL_SECONDS,
    )
    cache.delete(code_key)
    cache.delete(_password_reset_cache_key(normalized_email, PASSWORD_RESET_CACHE_SENT_SUFFIX))

    return {
        "ok": True,
        "message": "Code verified successfully.",
        "reset_authorization": reset_authorization,
    }


def confirm_password_reset(
    email: str, new_password: str, confirm_password: str, *, reset_authorization: str = ""
) -> dict:
    normalized_email = str(email or "").strip().lower()
    if not normalized_email:
        return {
            "ok": False,
            "message": "Email address is required.",
        }

    verified_key = _password_reset_cache_key(normalized_email, PASSWORD_RESET_CACHE_VERIFIED_SUFFIX)
    authorization = cache.get(verified_key)
    authorization_failure = {
        "ok": False,
        "message": "Reset session expired or code not verified. Please verify again.",
    }
    # Fail closed for missing proofs and legacy email-only verified flags.
    if (
        not isinstance(authorization, dict)
        or not isinstance(reset_authorization, str)
        or not reset_authorization
    ):
        return authorization_failure

    authorization_digest = authorization.get("authorization_digest")
    verified_password_hash = authorization.get("password_hash")
    verified_session_version = authorization.get("session_version")
    account_id = authorization.get("account_id")
    try:
        expires_ts = int(authorization.get("expires_at"))
    except (TypeError, ValueError):
        return authorization_failure
    if (
        int(timezone.now().timestamp()) >= expires_ts
        or not isinstance(account_id, int)
        or isinstance(verified_session_version, bool)
        or not isinstance(verified_session_version, int)
        or verified_session_version < 0
        or not isinstance(verified_password_hash, str)
        or not verified_password_hash
        or not isinstance(authorization_digest, str)
        or len(authorization_digest) != 64
        or any(character not in "0123456789abcdef" for character in authorization_digest)
        or not secrets.compare_digest(authorization_digest, sha256(reset_authorization.encode()).hexdigest())
    ):
        return authorization_failure

    if not isinstance(new_password, str) or not new_password:
        return {
            "ok": False,
            "message": "New password is required.",
        }

    if not isinstance(confirm_password, str) or new_password != confirm_password:
        return {
            "ok": False,
            "message": "Passwords do not match.",
        }

    requirement_errors = missing_password_requirements(new_password)
    if requirement_errors:
        return {
            "ok": False,
            "message": "Password does not meet requirements.",
            "errors": requirement_errors,
        }

    # A single conditional UPDATE makes the grant single-use even if concurrent
    # requests read the same cache value. It also cannot overwrite a newer password
    # or reset a different account that later acquires the same email address.
    updated = BookkeeperAccount.objects.filter(
        id=account_id,
        email__iexact=normalized_email,
        password_hash=verified_password_hash,
        session_version=verified_session_version,
    ).update(password_hash=make_password(new_password), session_version=F("session_version") + 1)
    if updated != 1:
        return authorization_failure
    cache.delete(verified_key)

    return {
        "ok": True,
        "message": "Password reset successfully.",
    }
