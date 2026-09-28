import logging
from decimal import Decimal

from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string

from safebooks.models import FinancialRecord, Period


logger = logging.getLogger(__name__)

DEFAULT_EMAIL_LOGO_URL = (
    "https://raw.githubusercontent.com/Yray0-9/FOR_UI/main/static/images/apple-touch-icon.png"
)


def _format_money(value) -> str:
    amount = value if isinstance(value, Decimal) else Decimal(str(value or "0"))
    return f"PHP {amount.quantize(Decimal('0.01')):,.2f}"


def _format_frequency(value: str) -> str:
    labels = dict(FinancialRecord.FREQUENCY_CHOICES)
    return labels.get(value, str(value or "").title() or "Monthly")


def _period_label(record: FinancialRecord) -> str:
    period = getattr(record, "period", None)
    if period:
        month_name = dict(Period.MONTH_CHOICES).get(period.month, str(period.month))
        return f"{month_name} {period.year}"

    if record.entry_date:
        return record.entry_date.strftime("%B %Y")

    return "the selected period"


def send_financial_record_created_email(record: FinancialRecord) -> dict:
    if not getattr(settings, "SAFEBOOKS_CLIENT_RECORD_EMAILS_ENABLED", True):
        return {
            "sent": False,
            "skipped": True,
            "reason": "Client record email notifications are disabled.",
        }

    bookkeeper = record.bookkeeper
    if not getattr(bookkeeper, "client_record_email_notifications_enabled", True):
        return {
            "sent": False,
            "skipped": True,
            "reason": "Client email notifications are turned off in Settings.",
        }

    client = record.client
    recipient_email = str(getattr(client, "email", "") or "").strip()
    if not recipient_email:
        return {
            "sent": False,
            "skipped": True,
            "reason": "Client email is not provided.",
        }

    bookkeeper_name = (
        str(getattr(bookkeeper, "full_name", "") or "").strip()
        or str(getattr(bookkeeper, "username", "") or "").strip()
        or "your bookkeeper"
    )
    bookkeeper_email = str(getattr(bookkeeper, "email", "") or "").strip()
    client_name = str(getattr(client, "client_name", "") or "Client").strip()
    period_label = _period_label(record)
    frequency_label = _format_frequency(record.frequency)
    total_amount_formatted = _format_money(record.total_amount)

    entry_date_formatted = (
        record.entry_date.strftime("%B %d, %Y")
        if record.entry_date
        else "N/A"
    )

    line_items_qs = record.line_items.all().order_by("sort_order", "id")
    line_item_count = line_items_qs.count()

    line_items_data = [
        {
            "description": item.description,
            "type_code": item.type_code,
            "amount": _format_money(item.amount),
        }
        for item in line_items_qs
    ]

    subject = f"SafeBooks record update for {period_label}"

    # Plain text fallback message ensuring strict backward compatibility and unit-test compliance
    message = (
        f"Hello {client_name},\n\n"
        "This is a SafeBooks update for your financial records.\n\n"
        f"{bookkeeper_name} recorded a {frequency_label.lower()} financial entry for {period_label}.\n"
        f"Entry date: {entry_date_formatted}\n"
        f"Total recorded amount: {total_amount_formatted}\n"
        f"Transactions recorded: {line_item_count}\n\n"
        "Please contact your bookkeeper if you need to review the details.\n\n"
        "SafeBooks"
    )

    logo_url = getattr(settings, "SAFEBOOKS_EMAIL_LOGO_URL", DEFAULT_EMAIL_LOGO_URL)

    # Rich HTML presentation context matching the SafeBooks design system
    html_context = {
        "client_name": client_name,
        "bookkeeper_name": bookkeeper_name,
        "bookkeeper_email": bookkeeper_email,
        "frequency_label": frequency_label,
        "period_label": period_label,
        "entry_date_formatted": entry_date_formatted,
        "total_amount_formatted": total_amount_formatted,
        "line_items": line_items_data,
        "line_item_count": line_item_count,
        "recipient_email": recipient_email,
        "logo_url": logo_url,
    }

    try:
        html_message = render_to_string(
            "emails/client_financial_record_notification.html",
            html_context,
        )
    except Exception:
        logger.warning(
            "Failed to render client record notification HTML template for record %s, falling back to plain text.",
            record.id,
            exc_info=True,
        )
        html_message = None

    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [recipient_email],
            html_message=html_message,
            fail_silently=False,
        )
    except Exception:
        logger.warning(
            "Failed to send financial record notification email for record %s.",
            record.id,
            exc_info=True,
        )
        return {
            "sent": False,
            "skipped": False,
            "reason": "Email delivery failed.",
        }

    return {
        "sent": True,
        "skipped": False,
        "reason": "",
    }
