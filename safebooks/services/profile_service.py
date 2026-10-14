from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import IntegrityError, transaction

from safebooks.models import BookkeeperAccount
from safebooks.services.auth_service import send_email_verification_code
from safebooks.validators.data_validator import model_text_errors


def _normalize_text(value) -> str:
    return str(value or "").strip()


def _serialize_bookkeeper(account: BookkeeperAccount) -> dict:
    return {
        "id": account.id,
        "full_name": account.full_name,
        "username": account.username,
        "email": account.email,
        "location": getattr(account, "location", "") or "",
        "status": account.status,
        "email_verified": account.email_verified,
        "login_alerts_enabled": bool(getattr(account, "login_alerts_enabled", False)),
    }


def get_profile_for_bookkeeper(bookkeeper: BookkeeperAccount) -> dict:
    return {
        "ok": True,
        "profile": _serialize_bookkeeper(bookkeeper),
    }


def update_profile_for_bookkeeper(bookkeeper: BookkeeperAccount, data: dict) -> dict:
    full_name = _normalize_text(data.get("full_name"))
    username = _normalize_text(data.get("username"))
    email = _normalize_text(data.get("email"))
    location = _normalize_text(data.get("location"))

    errors: list[str] = []

    if not full_name:
        errors.append("Full name is required.")
    if not username:
        errors.append("Username is required.")
    if not email:
        errors.append("Email is required.")

    errors.extend(model_text_errors(BookkeeperAccount, data))

    if email:
        try:
            validate_email(email)
        except ValidationError:
            errors.append("Email format is invalid.")

    if BookkeeperAccount.objects.filter(email__iexact=email).exclude(id=bookkeeper.id).exists():
        errors.append("Email already exists.")

    if BookkeeperAccount.objects.filter(username__iexact=username).exclude(id=bookkeeper.id).exists():
        errors.append("Username already exists.")

    if errors:
        return {
            "ok": False,
            "message": errors[0],
            "errors": errors,
        }

    current_email = str(bookkeeper.email or "")
    email_changed = email.lower() != current_email.lower()
    verification_result = None
    original_values = {field: getattr(bookkeeper, field) for field in ("full_name", "username", "location", "email", "email_verified")}

    bookkeeper.full_name = full_name
    bookkeeper.username = username
    bookkeeper.location = location

    update_fields = ["full_name", "username", "location"]
    if email_changed:
        bookkeeper.email = email
        bookkeeper.email_verified = False
        update_fields.extend(["email", "email_verified"])

    try:
        with transaction.atomic():
            # Reserve the new unique values before any verification email is sent.
            bookkeeper.save(update_fields=update_fields)
            if email_changed:
                verification_result = send_email_verification_code(bookkeeper, force=True)
                if not verification_result.get("ok"):
                    transaction.set_rollback(True)
                    for field, value in original_values.items():
                        setattr(bookkeeper, field, value)
                    return {"ok": False, "message": verification_result.get("message") or "Unable to send verification email."}
    except IntegrityError:
        for field, value in original_values.items():
            setattr(bookkeeper, field, value)
        if BookkeeperAccount.objects.filter(email__iexact=email).exclude(id=bookkeeper.id).exists():
            message = "Email already exists."
        elif BookkeeperAccount.objects.filter(username__iexact=username).exclude(id=bookkeeper.id).exists():
            message = "Username already exists."
        else:
            message = "Unable to update the profile. Refresh and try again."
        return {"ok": False, "message": message, "errors": [message]}

    return {
        "ok": True,
        "message": "Profile updated.",
        "user": _serialize_bookkeeper(bookkeeper),
        "requires_email_verification": bool(email_changed),
        "verification_sent": bool(verification_result and verification_result.get("ok")),
    }
