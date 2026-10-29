from django.db import models

from .financial_record_model import FinancialRecord


class FinancialRecordLine(models.Model):
    # Supporting worksheet figures are not additional financial movements.
    WORKSHEET_AMOUNT_LABELS = {
        "mict": "MICT",
        "cogs_cos": "COGS / COS",
        "income_payments_2307": "Income payments (2307)",
        "tax_withheld": "Tax withheld",
    }

    record = models.ForeignKey(
        FinancialRecord,
        on_delete=models.CASCADE,
        related_name="line_items",
    )
    type_code = models.CharField(max_length=80)
    description = models.CharField(max_length=255)
    # Null retains legacy entry remarks; an explicit blank means no form remark.
    remarks = models.CharField(max_length=255, null=True, blank=True)
    # Null preserves the parent record's original coverage for legacy entries.
    coverage_frequency = models.CharField(
        max_length=16, choices=FinancialRecord.FREQUENCY_CHOICES, null=True, blank=True,
    )
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    mict = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    cogs_cos = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    income_payments_2307 = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    tax_withheld = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "financial_record_lines"
        ordering = ["sort_order", "id"]
        indexes = [
            models.Index(fields=["record"]),
            models.Index(fields=["type_code"]),
        ]

    def __str__(self) -> str:
        return f"{self.type_code} - {self.amount}"
