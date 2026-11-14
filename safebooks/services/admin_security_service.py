import base64
import hashlib
import hmac
import secrets

import pyotp
import qrcode
import qrcode.image.svg
from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.db import transaction
from safebooks.services.session_security_service import save_account_security_change
from django.utils import timezone

from safebooks.models import AdminAccount, AdminAuditLog


TWO_FACTOR_ISSUER = "SafeBooks Admin"
RECOVERY_CODE_COUNT = 8


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


def _normalize_code(value) -> str:
    return str(value or "").strip().replace(" ", "").replace("-", "").upper()


def _looks_like_supported_hash(password_hash: str) -> bool:
    normalized_hash = str(password_hash or "")
    return normalized_hash.startswith((
        "pbkdf2_",
        "argon2$",
        "bcrypt$",
        "bcrypt_sha256$",
        "scrypt$",
    ))


def _verify_current_password(admin_account: AdminAccount, current_password: str) -> bool:
    stored_password_hash = str(admin_account.password_hash or "")
    if check_password(current_password, stored_password_hash):
        return True

    if stored_password_hash and not _looks_like_supported_hash(stored_password_hash):
        if current_password == stored_password_hash:
            admin_account.password_hash = make_password(current_password)
            admin_account.save(update_fields=["password_hash"])
            return True

    return False


def _is_totp_valid(secret: str, code: str) -> bool:
    normalized_code = _normalize_code(code)
    if not secret or len(normalized_code) != 6 or not normalized_code.isdigit():
        return False
    return pyotp.TOTP(secret).verify(normalized_code, valid_window=1)


def _generate_recovery_codes() -> list[str]:
    codes: list[str] = []
    while len(codes) < RECOVERY_CODE_COUNT:
        raw_code = secrets.token_hex(6).upper()
        formatted_code = f"{raw_code[:4]}-{raw_code[4:8]}-{raw_code[8:]}"
        if formatted_code not in codes:
            codes.append(formatted_code)
    return codes


def _hash_recovery_code(code: str) -> str:
    signing_key = str(settings.SECRET_KEY).encode("utf-8")
    normalized_code = _normalize_code(code).encode("utf-8")
    return hmac.new(signing_key, normalized_code, hashlib.sha256).hexdigest()


def _build_recovery_code_set() -> tuple[list[str], list[str]]:
    recovery_codes = _generate_recovery_codes()
    recovery_code_hashes = [_hash_recovery_code(code) for code in recovery_codes]
    return recovery_codes, recovery_code_hashes


def _find_recovery_code_index(admin_account: AdminAccount, code: str) -> int | None:
    normalized_code = _normalize_code(code)
    if not normalized_code:
        return None

    stored_codes = admin_account.two_factor_recovery_codes
    if not isinstance(stored_codes, list):
        return None

    candidate_hash = _hash_recovery_code(normalized_code)
    for index, stored_hash in enumerate(stored_codes):
        if hmac.compare_digest(candidate_hash, str(stored_hash or "")):
            return index
    return None


def _consume_recovery_code(admin_account: AdminAccount, index: int) -> None:
    stored_codes = list(admin_account.two_factor_recovery_codes or [])
    if index < 0 or index >= len(stored_codes):
        return
    stored_codes.pop(index)
    admin_account.two_factor_recovery_codes = stored_codes
    admin_account.save(update_fields=["two_factor_recovery_codes"])


def _create_security_audit(admin_account: AdminAccount, action_type: str, message: str) -> None:
    AdminAuditLog.objects.create(
        admin=admin_account,
        action_type=action_type,
        target_model="AdminAccount",
        target_id=admin_account.id,
        message=message,
        metadata={
            "admin_id": admin_account.id,
            "target_name": admin_account.full_name,
            "target_email": admin_account.email,
        },
    )


def get_admin_two_factor_status(admin_account: AdminAccount) -> dict:
    stored_codes = admin_account.two_factor_recovery_codes
    recovery_codes_remaining = len(stored_codes) if isinstance(stored_codes, list) else 0
    return {
        "enabled": bool(admin_account.two_factor_enabled and admin_account.two_factor_secret),
        "confirmed_at": (
            admin_account.two_factor_confirmed_at.isoformat()
            if admin_account.two_factor_confirmed_at
            else ""
        ),
        "recovery_codes_remaining": recovery_codes_remaining,
    }


def create_admin_two_factor_setup(admin_account: AdminAccount, payload: dict) -> dict:
    if admin_account.two_factor_enabled:
        return {
            "ok": False,
            "message": "Two-factor authentication is already enabled.",
        }

    current_password = str((payload or {}).get("current_password") or "")
    if not current_password:
        return {"ok": False, "message": "Current password is required."}
    if not _verify_current_password(admin_account, current_password):
        return {"ok": False, "message": "Current password is incorrect."}

    secret = pyotp.random_base32()
    account_label = str(admin_account.email or admin_account.full_name or "SafeBooks Admin").strip()
    provisioning_uri = pyotp.TOTP(secret).provisioning_uri(
        name=account_label,
        issuer_name=TWO_FACTOR_ISSUER,
    )
    return {
        "ok": True,
        "message": "Authenticator setup key generated.",
        "secret": secret,
        "otpauth_uri": provisioning_uri,
        "qr_code_data_url": _qr_code_data_url(provisioning_uri),
    }


def enable_admin_two_factor(admin_account: AdminAccount, setup_secret: str, payload: dict) -> dict:
    if admin_account.two_factor_enabled:
        return {
            "ok": False,
            "message": "Two-factor authentication is already enabled.",
        }
    if not setup_secret:
        return {
            "ok": False,
            "message": "Start authenticator setup again before confirming.",
        }

    code = str((payload or {}).get("code") or "")
    if not code:
        return {"ok": False, "message": "Authenticator code is required."}
    if not _is_totp_valid(setup_secret, code):
        return {"ok": False, "message": "Invalid authenticator code."}

    recovery_codes, recovery_code_hashes = _build_recovery_code_set()

    with transaction.atomic():
        admin_account.two_factor_enabled = True
        admin_account.two_factor_secret = setup_secret
        admin_account.two_factor_confirmed_at = timezone.now()
        admin_account.two_factor_recovery_codes = recovery_code_hashes
        save_account_security_change(admin_account, [
            "two_factor_enabled",
            "two_factor_secret",
            "two_factor_confirmed_at",
            "two_factor_recovery_codes",
        ])
        _create_security_audit(
            admin_account,
            AdminAuditLog.ACTION_ADMIN_TWO_FACTOR_ENABLED,
            "Enabled authenticator two-factor authentication.",
        )

    return {
        "ok": True,
        "message": "Two-factor authentication enabled. Save your recovery codes now.",
        "two_factor": get_admin_two_factor_status(admin_account),
        # Plaintext recovery codes are returned only by this confirmation
        # response. Only keyed hashes are persisted in the database.
        "recovery_codes": recovery_codes,
    }


def regenerate_admin_two_factor_recovery_codes(
    admin_account: AdminAccount,
    payload: dict,
) -> dict:
    if not admin_account.two_factor_enabled or not admin_account.two_factor_secret:
        return {"ok": False, "message": "Two-factor authentication is not enabled."}

    current_password = str((payload or {}).get("current_password") or "")
    code = str((payload or {}).get("code") or "")
    if not current_password:
        return {"ok": False, "message": "Current password is required."}
    if not _verify_current_password(admin_account, current_password):
        return {"ok": False, "message": "Current password is incorrect."}
    if not code:
        return {"ok": False, "message": "Authenticator code is required."}
    if not _is_totp_valid(admin_account.two_factor_secret, code):
        return {"ok": False, "message": "Invalid authenticator code."}

    recovery_codes, recovery_code_hashes = _build_recovery_code_set()
    with transaction.atomic():
        admin_account.two_factor_recovery_codes = recovery_code_hashes
        save_account_security_change(admin_account, ["two_factor_recovery_codes"])
        _create_security_audit(
            admin_account,
            AdminAuditLog.ACTION_ADMIN_TWO_FACTOR_RECOVERY_CODES_REGENERATED,
            "Replaced administrator two-factor recovery codes.",
        )

    return {
        "ok": True,
        "message": "New recovery codes created. Previous codes no longer work.",
        "two_factor": get_admin_two_factor_status(admin_account),
        "recovery_codes": recovery_codes,
    }


def verify_admin_two_factor_login(admin_account: AdminAccount, code: str) -> dict:
    if not admin_account.two_factor_enabled or not admin_account.two_factor_secret:
        return {"ok": False, "message": "Two-factor authentication is not enabled."}
    if not str(code or "").strip():
        return {"ok": False, "message": "Authenticator or recovery code is required."}

    if _is_totp_valid(admin_account.two_factor_secret, code):
        return {"ok": True, "recovery_code_used": False}

    with transaction.atomic():
        locked_account = AdminAccount.objects.select_for_update().get(pk=admin_account.pk)
        recovery_index = _find_recovery_code_index(locked_account, code)
        if recovery_index is None:
            return {"ok": False, "message": "Invalid authenticator or recovery code."}
        _consume_recovery_code(locked_account, recovery_index)
        admin_account.two_factor_recovery_codes = list(
            locked_account.two_factor_recovery_codes or []
        )
    return {"ok": True, "recovery_code_used": True}


def disable_admin_two_factor(admin_account: AdminAccount, payload: dict) -> dict:
    if not admin_account.two_factor_enabled:
        return {"ok": False, "message": "Two-factor authentication is not enabled."}

    current_password = str((payload or {}).get("current_password") or "")
    code = str((payload or {}).get("code") or "")
    if not current_password:
        return {"ok": False, "message": "Current password is required."}
    if not _verify_current_password(admin_account, current_password):
        return {"ok": False, "message": "Current password is incorrect."}

    verification = verify_admin_two_factor_login(admin_account, code)
    if not verification.get("ok"):
        return verification

    with transaction.atomic():
        admin_account.two_factor_enabled = False
        admin_account.two_factor_secret = ""
        admin_account.two_factor_confirmed_at = None
        admin_account.two_factor_recovery_codes = []
        save_account_security_change(admin_account, [
            "two_factor_enabled",
            "two_factor_secret",
            "two_factor_confirmed_at",
            "two_factor_recovery_codes",
        ])
        _create_security_audit(
            admin_account,
            AdminAuditLog.ACTION_ADMIN_TWO_FACTOR_DISABLED,
            "Disabled authenticator two-factor authentication.",
        )

    return {
        "ok": True,
        "message": "Two-factor authentication disabled.",
        "two_factor": get_admin_two_factor_status(admin_account),
    }
