from django.db import models
from django.db.models.functions import Upper


class AdminAccount(models.Model):
    full_name = models.CharField(max_length=120)
    email = models.EmailField(unique=True)
    password_hash = models.CharField(max_length=255)
    session_version = models.PositiveBigIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_login = models.DateTimeField(blank=True, null=True)
    # Optional setup; once enabled, every sign-in must complete the second factor.
    two_factor_enabled = models.BooleanField(default=False)
    two_factor_secret = models.CharField(max_length=64, blank=True, default="")
    two_factor_confirmed_at = models.DateTimeField(blank=True, null=True)
    two_factor_recovery_codes = models.JSONField(default=list, blank=True)

    class Meta:
        db_table = "admin_accounts"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(Upper("email"), name="admin_email_ci_unique"),
        ]

    def __str__(self) -> str:
        return f"{self.full_name} ({self.email})"


class AdminAuditLog(models.Model):
    ACTION_BOOKKEEPER_APPROVED = "bookkeeper.approved"
    ACTION_BOOKKEEPER_REJECTED = "bookkeeper.rejected"
    ACTION_BOOKKEEPER_DEACTIVATED = "bookkeeper.deactivated"
    ACTION_BOOKKEEPER_REACTIVATED = "bookkeeper.reactivated"
    ACTION_BOOKKEEPER_DELETED = "bookkeeper.deleted"
    ACTION_BOOKKEEPER_DEACTIVATION_REQUESTED = "bookkeeper.deactivation_requested"
    ACTION_BOOKKEEPER_DEACTIVATION_DECLINED = "bookkeeper.deactivation_declined"
    ACTION_ADMIN_PROFILE_UPDATED = "admin.profile_updated"
    ACTION_ADMIN_PASSWORD_CHANGED = "admin.password_changed"
    ACTION_ADMIN_LOGIN = "admin.login"
    ACTION_ADMIN_LOGOUT = "admin.logout"
    ACTION_ADMIN_TWO_FACTOR_ENABLED = "admin.two_factor_enabled"
    ACTION_ADMIN_TWO_FACTOR_DISABLED = "admin.two_factor_disabled"
    ACTION_ADMIN_TWO_FACTOR_RECOVERY_CODES_REGENERATED = "admin.two_factor_recovery_codes_regenerated"

    admin = models.ForeignKey(
        AdminAccount,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
    )
    action_type = models.CharField(max_length=80, db_index=True)
    target_model = models.CharField(max_length=80)
    target_id = models.PositiveIntegerField(null=True, blank=True)
    message = models.CharField(max_length=255)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "admin_audit_logs"
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["action_type", "-created_at"], name="admin_audit_action_idx"),
            models.Index(fields=["target_model", "target_id"], name="admin_audit_target_idx"),
        ]

    def __str__(self) -> str:
        return self.message
