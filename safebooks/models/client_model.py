from django.db import models

from .user_model import BookkeeperAccount


class Client(models.Model):
    REMARK_NEW = "new"
    REMARK_ACTIVE = "active"
    REMARK_SEPARATED = "separated"
    REMARK_CLOSED = "closed"

    REMARK_CHOICES = [
        (REMARK_NEW, "New"),
        (REMARK_ACTIVE, "Active"),
        (REMARK_SEPARATED, "Separated"),
        (REMARK_CLOSED, "Closed"),
    ]


    bookkeeper = models.ForeignKey(
        BookkeeperAccount,
        on_delete=models.CASCADE,
        related_name="clients",
    )
    client_name = models.CharField(max_length=160)
    tin_number = models.CharField(max_length=40, unique=True)
    trade_name = models.CharField(max_length=180, blank=True, default="")
    location = models.CharField(max_length=180)
    permit_number = models.CharField(max_length=80, blank=True, default="")
    birthday = models.DateField(null=True, blank=True)
    email = models.EmailField(blank=True, default="")
    email_password = models.CharField(max_length=255, blank=True, default="")
    orus_account = models.CharField(max_length=255, blank=True, default="")
    orus_password = models.CharField(max_length=255, blank=True, default="")
    custom_fields = models.JSONField(blank=True, default=list)
    forecast_growth_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    remarks = models.CharField(
        max_length=20,
        choices=REMARK_CHOICES,
        default=REMARK_NEW,
    )
    closure_reason = models.CharField(max_length=255, blank=True, default="")
    closure_notes = models.TextField(blank=True, default="")
    closed_at = models.DateTimeField(null=True, blank=True)
    date_registered = models.DateField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "clients"
        ordering = ["client_name", "id"]
        indexes = [
            models.Index(fields=["bookkeeper"]),
            models.Index(fields=["client_name"]),
            models.Index(fields=["remarks"]),
        ]

    def __str__(self) -> str:
        return f"{self.client_name} ({self.tin_number})"
