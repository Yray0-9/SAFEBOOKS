import base64
import re

import pyotp
import qrcode
import qrcode.image.svg
from django.contrib.auth.hashers import check_password, make_password
from django.utils import timezone

from safebooks.validators.password_validator import missing_password_requirements


TWO_FACTOR_ISSUER = "SafeBooks"
_CODE_CLEANUP_RE = re.compile(r"\D+")


def _normalize_text(value) -> str:
    return str(value or "").strip()


def _normalize_code(value) -> str:
    return _CODE_CLEANUP_RE.sub("", str(value or ""))


def _normalize_bool(value):
    if isinstance(value, bool):
        return value
    if value is None:
        return None
    cleaned = str(value).strip().lower()
    if cleaned in {"true", "1", "yes", "on"}:
        return True
    if cleaned in {"false", "0", "no", "off"}:
        return False
    return None


def _looks_like_supported_hash(password_hash: str) -> bool:
    normalized_hash = str(password_hash or "")
    return normalized_hash.startswith((
        "pbkdf2_",
        "argon2$",
        "bcrypt$",
        "bcrypt_sha256$",
        "scrypt$",
    ))


def _verify_current_password(account, current_password: str) -> bool:
    stored_password_hash = str(account.password_hash or "")
    if check_password(current_password, stored_password_hash):
        return True

    # Backward compatibility for early records that stored raw passwords.
    if stored_password_hash and not _looks_like_supported_hash(stored_password_hash):
        if current_password == stored_password_hash:
            account.password_hash = make_password(current_password)
            account.save(update_fields=["password_hash"])
            return True

    return False


def change_bookkeeper_password(bookkeeper, payload: dict) -> dict:
    if not isinstance(payload, dict):
        return {
            "ok": False,
            "message": "Invalid request payload.",
            "errors": ["Invalid request payload."],
        }

    current_password = str(payload.get("current_password", ""))
    new_password = str(payload.get("new_password", ""))
    confirm_password = str(payload.get("confirm_password", ""))

    errors: list[str] = []

    if not current_password:
        errors.append("Current password is required.")
    if not new_password:
        errors.append("New password is required.")
    if new_password and confirm_password and new_password != confirm_password:
        errors.append("New passwords do not match.")
    if new_password and current_password and new_password == current_password:
        errors.append("New password must be different from the current password.")

    password_requirement_errors = missing_password_requirements(new_password)
    if new_password and password_requirement_errors:
        errors.append("Password does not meet requirements.")

    if errors:
        return {
            "ok": False,
            "message": errors[0],
            "errors": errors,
            "password_requirements": password_requirement_errors,
        }

    if not _verify_current_password(bookkeeper, current_password):
        return {
            "ok": False,
            "message": "Current password is incorrect.",
            "errors": ["Current password is incorrect."],
        }

    bookkeeper.password_hash = make_password(new_password)
    bookkeeper.save(update_fields=["password_hash"])

    return {
        "ok": True,
        "message": "Password updated successfully.",
    }


def update_login_alerts_preference(bookkeeper, payload: dict) -> dict:
    if not isinstance(payload, dict):
        return {
            "ok": False,
            "message": "Invalid request payload.",
            "errors": ["Invalid request payload."],
        }

    enabled_value = _normalize_bool(payload.get("enabled"))
    if enabled_value is None:
        return {
            "ok": False,
            "message": "Login alerts setting is required.",
            "errors": ["Login alerts setting is required."],
        }

    bookkeeper.login_alerts_enabled = enabled_value
    bookkeeper.save(update_fields=["login_alerts_enabled"])

    return {
        "ok": True,
        "message": "Login alerts preference updated.",
        "login_alerts_enabled": enabled_value,
    }


def confirm_client_details_access(bookkeeper, payload: dict) -> dict:
    if not isinstance(payload, dict):
        return {
            "ok": False,
            "message": "Invalid request payload.",
            "errors": ["Invalid request payload."],
        }

    current_password = str(payload.get("current_password", ""))
    if not current_password:
        return {
            "ok": False,
            "message": "Password is required.",
            "errors": ["Password is required."],
        }

    if not _verify_current_password(bookkeeper, current_password):
        return {
            "ok": False,
            "message": "Password is incorrect.",
            "errors": ["Password is incorrect."],
        }

    return {
        "ok": True,
        "message": "Client details access confirmed.",
    }


def update_client_details_access_preference(bookkeeper, payload: dict) -> dict:
    if not isinstance(payload, dict):
        return {
            "ok": False,
            "message": "Invalid request payload.",
            "errors": ["Invalid request payload."],
        }

    enabled_value = _normalize_bool(payload.get("enabled"))
    if enabled_value is None:
        return {
            "ok": False,
            "message": "Client details lock setting is required.",
            "errors": ["Client details lock setting is required."],
        }

    current_password = str(payload.get("current_password", ""))
    if not current_password:
        return {
            "ok": False,
            "message": "Current password is required.",
            "errors": ["Current password is required."],
        }

    if not _verify_current_password(bookkeeper, current_password):
        return {
            "ok": False,
            "message": "Current password is incorrect.",
            "errors": ["Current password is incorrect."],
        }

    bookkeeper.client_details_password_required = enabled_value
    bookkeeper.save(update_fields=["client_details_password_required"])

    return {
        "ok": True,
        "message": "Client details lock preference updated.",
        "client_details_password_required": enabled_value,
    }


def _build_totp_secret() -> str:
    return pyotp.random_base32()


def _build_provisioning_uri(secret: str, account_label: str) -> str:
    return pyotp.TOTP(secret).provisioning_uri(name=account_label, issuer_name=TWO_FACTOR_ISSUER)


def _qr_code_data_url(value: str) -> str:
    image = qrcode.make(
        value,
        image_factory=qrcode.image.svg.SvgPathImage,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        border=4,
    )
    svg_bytes = image.to_string()
    encoded = base64.b64encode(svg_bytes).decode("ascii")
    return f"data:image/svg+xml;base64,{encoded}"


def _is_two_factor_code_valid(secret: str, code: str) -> bool:
    if not secret:
        return False
    normalized_code = _normalize_code(code)
    if len(normalized_code) != 6 or not normalized_code.isdigit():
        return False

    return pyotp.TOTP(secret).verify(normalized_code, valid_window=1)


def get_bookkeeper_two_factor_status(bookkeeper) -> dict:
    return {
        "enabled": bool(bookkeeper.two_factor_enabled and bookkeeper.two_factor_secret),
        "confirmed_at": (
            bookkeeper.two_factor_confirmed_at.isoformat()
            if bookkeeper.two_factor_confirmed_at
            else ""
        ),
    }


def create_bookkeeper_two_factor_setup(bookkeeper) -> dict:
    if bookkeeper.two_factor_enabled and bookkeeper.two_factor_secret:
        return {
            "ok": False,
            "message": "Two-factor authentication is already enabled.",
        }

    secret = _build_totp_secret()
    account_label = _normalize_text(bookkeeper.email) or _normalize_text(bookkeeper.username) or "SafeBooks"
    provisioning_uri = _build_provisioning_uri(secret, account_label)
    qr_data_url = _qr_code_data_url(provisioning_uri)

    return {
        "ok": True,
        "message": "Two-factor setup key generated.",
        "secret": secret,
        "otpauth_uri": provisioning_uri,
        "provisioning_uri": provisioning_uri,
        "qr_code_data_url": qr_data_url,
    }


def enable_bookkeeper_two_factor(bookkeeper, setup_secret: str, payload: dict) -> dict:
    if bookkeeper.two_factor_enabled and bookkeeper.two_factor_secret:
        return {
            "ok": False,
            "message": "Two-factor authentication is already enabled.",
        }

    if not setup_secret:
        return {
            "ok": False,
            "message": "Start authenticator setup again before confirming.",
        }

    if not isinstance(payload, dict):
        return {
            "ok": False,
            "message": "Invalid request payload.",
            "errors": ["Invalid request payload."],
        }

    code = payload.get("code") or payload.get("token") or payload.get("otp")
    if not code:
        return {
            "ok": False,
            "message": "Authenticator code is required.",
            "errors": ["Authenticator code is required."],
        }

    if not _is_two_factor_code_valid(setup_secret, str(code)):
        return {
            "ok": False,
            "message": "Invalid authenticator code. Please check your authenticator app and try again.",
            "errors": ["Invalid authenticator code."],
        }

    bookkeeper.two_factor_enabled = True
    bookkeeper.two_factor_secret = setup_secret
    bookkeeper.two_factor_confirmed_at = timezone.now()
    bookkeeper.save(update_fields=["two_factor_enabled", "two_factor_secret", "two_factor_confirmed_at"])

    status_dict = get_bookkeeper_two_factor_status(bookkeeper)
    return {
        "ok": True,
        "message": "Two-factor authentication enabled successfully.",
        "two_factor_enabled": True,
        "two_factor": status_dict,
    }


def disable_bookkeeper_two_factor(bookkeeper, payload: dict) -> dict:
    if not isinstance(payload, dict):
        return {
            "ok": False,
            "message": "Invalid request payload.",
            "errors": ["Invalid request payload."],
        }

    current_password = str(payload.get("current_password", ""))
    if not current_password:
        return {
            "ok": False,
            "message": "Current password is required.",
            "errors": ["Current password is required."],
        }

    if not _verify_current_password(bookkeeper, current_password):
        return {
            "ok": False,
            "message": "Current password is incorrect.",
            "errors": ["Current password is incorrect."],
        }

    bookkeeper.two_factor_enabled = False
    bookkeeper.two_factor_secret = ""
    bookkeeper.two_factor_confirmed_at = None
    bookkeeper.save(update_fields=["two_factor_enabled", "two_factor_secret", "two_factor_confirmed_at"])

    status_dict = get_bookkeeper_two_factor_status(bookkeeper)
    return {
        "ok": True,
        "message": "Two-factor authentication disabled successfully.",
        "two_factor_enabled": False,
        "two_factor": status_dict,
    }


def verify_bookkeeper_two_factor_login(bookkeeper, code: str) -> dict:
    if not bookkeeper.two_factor_enabled or not bookkeeper.two_factor_secret:
        return {
            "ok": False,
            "message": "Two-factor authentication is not enabled.",
            "errors": ["Two-factor authentication is not enabled."],
        }

    if not code:
        return {
            "ok": False,
            "message": "Authenticator code is required.",
            "errors": ["Authenticator code is required."],
        }

    if not _is_two_factor_code_valid(bookkeeper.two_factor_secret, str(code)):
        return {
            "ok": False,
            "message": "Invalid authenticator code.",
            "errors": ["Invalid authenticator code."],
        }

    return {
        "ok": True,
        "message": "Two-factor verification successful.",
    }


# Backwards compatibility aliases
create_two_factor_setup = create_bookkeeper_two_factor_setup
enable_two_factor = enable_bookkeeper_two_factor
disable_two_factor = disable_bookkeeper_two_factor
verify_two_factor_login = verify_bookkeeper_two_factor_login
