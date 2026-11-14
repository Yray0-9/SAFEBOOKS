from django.contrib.auth.hashers import check_password, make_password
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import IntegrityError, transaction

from safebooks.models import AdminAccount, AdminAuditLog
from safebooks.services.admin_audit_service import ACTION_LABELS
from safebooks.services.admin_security_service import get_admin_two_factor_status
from safebooks.services.session_security_service import save_account_security_change
from safebooks.validators.password_validator import missing_password_requirements
from safebooks.validators.data_validator import model_text_errors


def _normalize_text(value) -> str:
    return str(value or "").strip()


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


def _serialize_admin(account: AdminAccount) -> dict:
    return {
        "id": account.id,
        "full_name": account.full_name,
        "email": account.email,
        "is_active": bool(account.is_active),
        "created_at": account.created_at.isoformat() if account.created_at else "",
        "last_login": account.last_login.isoformat() if account.last_login else "",
        "role_label": "System Manager",
    }


def _serialize_activity(log: AdminAuditLog) -> dict:
    return {
        "id": log.id,
        "action_type": log.action_type,
        "action_label": ACTION_LABELS.get(log.action_type, log.action_type.replace(".", " ").title()),
        "message": log.message,
        "created_at": log.created_at.isoformat() if log.created_at else "",
    }


def _create_admin_profile_audit_log(admin_account: AdminAccount, action_type: str, message: str, metadata: dict | None = None) -> None:
    AdminAuditLog.objects.create(
        admin=admin_account,
        action_type=action_type,
        target_model="AdminAccount",
        target_id=admin_account.id,
        message=message,
        metadata={
            "admin_id": admin_account.id,
            "admin_name": admin_account.full_name,
            "admin_email": admin_account.email,
            "target_name": admin_account.full_name,
            "target_email": admin_account.email,
            **(metadata or {}),
        },
    )


def get_admin_profile(admin_account: AdminAccount) -> dict:
    recent_logs = AdminAuditLog.objects.filter(admin=admin_account).order_by("-created_at", "-id")[:5]
    return {
        "ok": True,
        "profile": _serialize_admin(admin_account),
        "two_factor": get_admin_two_factor_status(admin_account),
        "recent_activity": [_serialize_activity(log) for log in recent_logs],
    }


def update_admin_profile(admin_account: AdminAccount, payload: dict) -> dict:
    if not isinstance(payload, dict):
        return {
            "ok": False,
            "message": "Invalid request payload.",
            "errors": ["Invalid request payload."],
        }

    full_name = _normalize_text(payload.get("full_name"))
    email = _normalize_text(payload.get("email")).lower()

    errors: list[str] = []
    if not full_name:
        errors.append("Full name is required.")
    if not email:
        errors.append("Email is required.")

    errors.extend(model_text_errors(AdminAccount, payload))

    if email:
        try:
            validate_email(email)
        except ValidationError:
            errors.append("Email format is invalid.")

    if email and AdminAccount.objects.filter(email__iexact=email).exclude(id=admin_account.id).exists():
        errors.append("Email already exists.")

    if errors:
        return {
            "ok": False,
            "message": errors[0],
            "errors": errors,
        }

    changed_fields: list[str] = []
    old_email = admin_account.email

    if full_name != (admin_account.full_name or ""):
        changed_fields.append("full_name")
    if email.lower() != str(admin_account.email or "").lower():
        changed_fields.append("email")

    if not changed_fields:
        return {
            "ok": True,
            "message": "Profile is already up to date.",
            "profile": _serialize_admin(admin_account),
            "recent_activity": get_admin_profile(admin_account)["recent_activity"],
        }

    old_name = admin_account.full_name
    try:
        with transaction.atomic():
            admin_account.full_name = full_name
            admin_account.email = email
            admin_account.save(update_fields=["full_name", "email"])
            _create_admin_profile_audit_log(
                admin_account, AdminAuditLog.ACTION_ADMIN_PROFILE_UPDATED, "Updated admin profile details.",
                {"changed_fields": changed_fields, "old_email": old_email},
            )
    except IntegrityError:
        admin_account.full_name = old_name
        admin_account.email = old_email
        message = "Email already exists." if AdminAccount.objects.filter(email__iexact=email).exclude(id=admin_account.id).exists() else "Unable to update the profile. Refresh and try again."
        return {"ok": False, "message": message, "errors": [message]}

    return {
        "ok": True,
        "message": "Admin profile updated.",
        "profile": _serialize_admin(admin_account),
        "recent_activity": get_admin_profile(admin_account)["recent_activity"],
    }


def change_admin_password(admin_account: AdminAccount, payload: dict) -> dict:
    if not isinstance(payload, dict):
        return {
            "ok": False,
            "message": "Invalid request payload.",
            "errors": ["Invalid request payload."],
        }

    current_password = str(payload.get("current_password") or "")
    new_password = str(payload.get("new_password") or "")
    confirm_password = str(payload.get("confirm_password") or "")
    password_requirement_errors = missing_password_requirements(new_password) if new_password else []

    errors: list[str] = []
    if not current_password:
        errors.append("Current password is required.")
    if not new_password:
        errors.append("New password is required.")
    if not confirm_password:
        errors.append("Confirm password is required.")
    if new_password and confirm_password and new_password != confirm_password:
        errors.append("New passwords do not match.")
    if new_password and current_password and new_password == current_password:
        errors.append("New password must be different from the current password.")
    if new_password and password_requirement_errors:
        errors.append("Password does not meet requirements.")

    if errors:
        return {
            "ok": False,
            "message": errors[0],
            "errors": errors,
            "password_requirements": password_requirement_errors,
        }

    if not _verify_current_password(admin_account, current_password):
        return {
            "ok": False,
            "message": "Current password is incorrect.",
            "errors": ["Current password is incorrect."],
        }

    with transaction.atomic():
        admin_account.password_hash = make_password(new_password)
        save_account_security_change(admin_account, ["password_hash"])
        _create_admin_profile_audit_log(
            admin_account,
            AdminAuditLog.ACTION_ADMIN_PASSWORD_CHANGED,
            "Changed admin account password.",
        )

    return {
        "ok": True,
        "message": "Admin password updated.",
        "recent_activity": get_admin_profile(admin_account)["recent_activity"],
    }
