import logging

from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

from safebooks.models import AdminAuditLog, BookkeeperAccount
from safebooks.services.email_delivery_service import email_count_confirmed, preview_only_email_backend


logger = logging.getLogger(__name__)

DELIVERY_SENT = "sent"
DELIVERY_SKIPPED = "skipped"
DELIVERY_FAILED = "failed"


def _delivery_result(status: str, reason: str = "") -> dict:
    return {
        "status": status,
        "reason": str(reason or "").strip(),
    }


def send_approval_decision_email(account: BookkeeperAccount, action_type: str) -> dict:
    if not getattr(settings, "SAFEBOOKS_APPROVAL_DECISION_EMAILS_ENABLED", True):
        return _delivery_result(DELIVERY_SKIPPED, "Approval decision emails are disabled.")

    recipient_email = str(account.email or "").strip()
    if not recipient_email:
        return _delivery_result(DELIVERY_SKIPPED, "Bookkeeper email is not provided.")
    if preview_only_email_backend():
        return _delivery_result(DELIVERY_SKIPPED, "The local email backend does not send emails to inboxes.")

    display_name = str(account.full_name or account.username or "Bookkeeper").strip()
    if action_type == AdminAuditLog.ACTION_BOOKKEEPER_APPROVED:
        subject = "Your SafeBooks access request was approved"
        message = (
            f"Hello {display_name},\n\n"
            "Your SafeBooks access request has been approved. "
            "You can now sign in to your SafeBooks workspace using your registered account.\n\n"
            "If you did not request this access or need help, contact your SafeBooks system manager.\n\n"
            "SafeBooks"
        )
    elif action_type == AdminAuditLog.ACTION_BOOKKEEPER_REJECTED:
        rejection_reason = str(account.rejection_reason or "No reason was provided.").strip()
        subject = "Update on your SafeBooks access request"
        message = (
            f"Hello {display_name},\n\n"
            "Your SafeBooks access request was not approved.\n\n"
            f"Reason: {rejection_reason}\n\n"
            "Review the reason above and contact your SafeBooks system manager if details need to be corrected.\n\n"
            "SafeBooks"
        )
    else:
        return _delivery_result(DELIVERY_SKIPPED, "This decision does not send an email.")

    try:
        sent_count = send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [recipient_email],
            fail_silently=False,
        )
    except Exception as error:
        logger.warning(
            "Approval email failed (%s).", type(error).__name__,
        )
        return _delivery_result(DELIVERY_FAILED, "Email delivery failed.")

    if not email_count_confirmed(sent_count):
        return _delivery_result(DELIVERY_FAILED, "The email backend did not confirm delivery.")
    return _delivery_result(DELIVERY_SENT)


def save_delivery_outcome(audit_log: AdminAuditLog, delivery: dict, *, is_retry: bool = False) -> dict:
    metadata = dict(audit_log.metadata or {})
    previous_delivery = metadata.get("email_delivery")
    if not isinstance(previous_delivery, dict):
        previous_delivery = {}

    retry_count = int(previous_delivery.get("retry_count") or 0)
    if is_retry:
        retry_count += 1

    saved_delivery = {
        "status": str(delivery.get("status") or DELIVERY_FAILED),
        "reason": str(delivery.get("reason") or "").strip()[:255],
        "attempted_at": timezone.now().isoformat(),
        "retry_count": retry_count,
    }
    metadata["email_delivery"] = saved_delivery
    audit_log.metadata = metadata
    audit_log.save(update_fields=["metadata"])
    return saved_delivery


def format_decision_result_message(base_message: str, delivery: dict) -> str:
    status = str(delivery.get("status") or "")
    reason = str(delivery.get("reason") or "").strip()
    if status == DELIVERY_SENT:
        return f"{base_message} Decision email accepted for delivery."
    if status == DELIVERY_SKIPPED:
        return f"{base_message} Decision email skipped: {reason}"
    return f"{base_message} Decision saved, but email delivery failed."
