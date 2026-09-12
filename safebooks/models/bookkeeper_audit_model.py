from django.db import models

from .user_model import BookkeeperAccount


class BookkeeperAuditLog(models.Model):
    ACTION_CLIENT_CREATED = "client.created"
    ACTION_CLIENT_UPDATED = "client.updated"
    ACTION_CLIENT_CLOSED = "client.closed"
    ACTION_RECORD_CREATED = "record.created"
    ACTION_RECORD_UPDATED = "record.updated"
    ACTION_RECORD_DELETED = "record.deleted"
    ACTION_PROFILE_UPDATED = "profile.updated"
    ACTION_PASSWORD_CHANGED = "security.password_changed"
    ACTION_LOGIN_ALERTS_CHANGED = "settings.login_alerts_changed"
    ACTION_CLIENT_DETAILS_LOCK_CHANGED = "settings.client_details_lock_changed"
    ACTION_CLIENT_EMAILS_CHANGED = "settings.client_emails_changed"
    ACTION_DEACTIVATION_REQUESTED = "account.deactivation_requested"
    ACTION_TWO_FACTOR_ENABLED = "security.two_factor_enabled"
    ACTION_TWO_FACTOR_DISABLED = "security.two_factor_disabled"

    bookkeeper = models.ForeignKey(
        BookkeeperAccount,
        on_delete=models.CASCADE,
        related_name="audit_logs",
    )
    action_type = models.CharField(max_length=80, db_index=True)
    target_model = models.CharField(max_length=80, blank=True, default="")
    target_id = models.PositiveIntegerField(null=True, blank=True)
    message = models.CharField(max_length=255)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "bookkeeper_audit_logs"
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["bookkeeper", "-created_at"], name="bk_audit_owner_time_idx"),
            models.Index(fields=["bookkeeper", "action_type"], name="bk_audit_owner_action_idx"),
            models.Index(fields=["target_model", "target_id"], name="bk_audit_target_idx"),
        ]

    def __str__(self) -> str:
        return self.message
